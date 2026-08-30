"""The read-only Postgres login that generated analysis SQL runs as.

The app itself connects as the `postgres` superuser, so the only thing standing
between a hallucinated `DROP TABLE` and the data is a transaction that happens
never to be committed. Code the model writes gets its own role instead: SELECT
and nothing else, with `default_transaction_read_only` and a statement timeout
pinned to the role so they hold however the client chooses to connect.

Run as a script (`python -m db.readonly`) from `start.sh`, after the migrations
so the grants cover whatever alembic just created.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

from config import settings

# Long enough for a month-over-month aggregate over years of rows, short enough
# that an accidental cartesian join doesn't pin a Postgres backend on the Pi.
STATEMENT_TIMEOUT = "10s"


def _conninfo(user: str, password: str) -> str:
    """A libpq conninfo string, not a SQLAlchemy URL: `psycopg.connect` can't
    parse the `postgresql+psycopg://` dialect prefix `build_connection_string`
    adds, and `make_conninfo` quotes passwords that a URL would mangle."""
    return make_conninfo(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=user,
        password=password,
        dbname=settings.POSTGRES_DB,
    )


def readonly_conninfo() -> str:
    return _conninfo(
        settings.POSTGRES_READONLY_USER, settings.POSTGRES_READONLY_PASSWORD
    )


@contextmanager
def readonly_connection() -> Generator[psycopg.Connection]:
    """A connection that cannot write, even if the role's grants are wrong.

    Deliberately not a SQLAlchemy engine: the caller is a short-lived, one-shot
    sandbox process, and a second connection pool is the last thing this Pi
    needs.
    """
    conn = psycopg.connect(readonly_conninfo())
    try:
        # Redundant with the role's `default_transaction_read_only`, and kept
        # anyway so the guarantee is visible where the query actually runs.
        conn.read_only = True
        yield conn
    finally:
        conn.close()


@asynccontextmanager
async def async_readonly_connection() -> AsyncGenerator[psycopg.AsyncConnection]:
    """The same guarantee for callers already on the bot's event loop.

    A fresh connection per query rather than a pool: direct queries only happen
    when the user asks a question, so there is nothing worth keeping warm.
    """
    conn = await psycopg.AsyncConnection.connect(readonly_conninfo())
    try:
        await conn.set_read_only(True)
        yield conn
    finally:
        await conn.close()


def bootstrap_readonly_role() -> None:
    """Create the role and its grants, or bring an existing one back in line."""
    role = settings.POSTGRES_READONLY_USER
    password = settings.POSTGRES_READONLY_PASSWORD
    if not role or not password:
        raise RuntimeError(
            "POSTGRES_READONLY_USER and POSTGRES_READONLY_PASSWORD must both be "
            "set; refusing to create a login role without a password."
        )

    role_id = sql.Identifier(role)
    with (
        psycopg.connect(
            _conninfo(settings.POSTGRES_USER, settings.POSTGRES_PASSWORD),
            autocommit=True,
        ) as conn,
        conn.cursor() as cur,
    ):
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
        existed = cur.fetchone() is not None

        if existed:
            # Re-applied rather than skipped, so rotating the password in .env
            # is all it takes to rotate it here.
            cur.execute(
                sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(
                    role_id, sql.Literal(password)
                )
            )
        else:
            cur.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN PASSWORD {} "
                    "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT"
                ).format(role_id, sql.Literal(password))
            )

        # Attached to the role rather than the connection, so a client that
        # forgets to ask for them still gets them.
        cur.execute(
            sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(
                role_id
            )
        )
        cur.execute(
            sql.SQL("ALTER ROLE {} SET statement_timeout = {}").format(
                role_id, sql.Literal(STATEMENT_TIMEOUT)
            )
        )

        cur.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(settings.POSTGRES_DB), role_id
            )
        )
        cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role_id))
        cur.execute(
            sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(role_id)
        )
        # `ON ALL TABLES` only covers the tables that exist right now. Without
        # this line the next migration adds one the role silently cannot read.
        cur.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {}"
            ).format(role_id)
        )

    print(f"[readonly-role] {role} {'updated' if existed else 'created'}")


def verify_readonly() -> None:
    """Prove the role reads and cannot write, rather than assuming the grants
    landed. One connection per boot, and it turns a silently over-privileged
    role — which looks exactly like a correct one — into a loud failure."""
    with readonly_connection() as conn, conn.cursor() as cur:
        try:
            cur.execute("SELECT count(*) FROM transactions")
            (count,) = cur.fetchone()  # type: ignore[misc]
            read = f"can read transactions ({count} rows)"
        except psycopg.errors.UndefinedTable:
            # Migrations have not run yet; the grants are still worth checking.
            conn.rollback()
            read = "transactions table not created yet"

        try:
            cur.execute("CREATE TABLE _watson_ro_probe (x int)")
        except (
            psycopg.errors.ReadOnlySqlTransaction,
            psycopg.errors.InsufficientPrivilege,
        ):
            pass
        else:
            raise RuntimeError(
                f"{settings.POSTGRES_READONLY_USER} was able to create a table; "
                "the read-only role is not actually read-only."
            )
        finally:
            # Undoes the probe whichever way it went — DDL is transactional here.
            conn.rollback()

    print(f"[readonly-role] verified: {read}, cannot write")


if __name__ == "__main__":
    try:
        bootstrap_readonly_role()
        verify_readonly()
    except Exception as exc:
        # Loud but non-fatal: the bot, API and dashboard all work fine without
        # this role, so a failure here should not crash-loop the container.
        print(f"[readonly-role] FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
