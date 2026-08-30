"""Read-only SQL over the finance database, as a capability of its own.

The query does not belong to the transactions capability: charts need rows to
plot, reminders will want the same reach, and every one of them would otherwise
carry a copy of the schema. Keeping the tool and the DDL the model writes against
in one place means the others just name it.
"""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from psycopg.rows import dict_row
from pydantic_ai import ModelRetry
from pydantic_ai.capabilities import Capability
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from db.models import MonthlyBudget, Reminder, Tag, Transaction
from db.readonly import async_readonly_connection

# Rows travel through the model's context, not a sandbox, so this caps what fits
# in a prompt rather than what Postgres can manage.
MAX_ROWS = 500

# Generated from the ORM models so the schema shown to the LLM never drifts.
SCHEMA_REFERENCE = "\n".join(
    str(CreateTable(model.__table__).compile(dialect=postgresql.dialect()))  # type: ignore[arg-type]
    for model in (Transaction, Tag, MonthlyBudget, Reminder)
)


def _jsonable(value: Any) -> Any:
    """Whatever psycopg hands back, in a shape that survives the trip to the model."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (list, tuple)):  # text[] tags, arrays
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):  # json / jsonb
        return {str(k): _jsonable(v) for k, v in value.items()}
    return str(value)  # uuid, interval, range, inet, bytes: anything else


database = Capability(
    id="database",
    description="Read the finance database directly with read-only SQL.",
    defer_loading=True,
    instructions=f"""\
Database domain:
- `query_database` runs one statement as a role that holds SELECT and nothing
  else, under a 10s timeout. A write or a DDL statement fails rather than
  touching anything, so there is no harm in trying a query that might not work.
- Aggregate in SQL. At most {MAX_ROWS} rows come back and every one of them
  lands in your context, so GROUP BY, SUM and date_trunc beat fetching
  transactions and adding them up yourself.
- `tags` is a text[] of tag slugs: match it with `'slug' = ANY(tags)` or
  `tags @> ARRAY['slug']`, never with `=`.
- Amounts are NPR. Dates come back as ISO strings, ready to put straight into a
  chart spec.

Schema:
{SCHEMA_REFERENCE}
""",
)


@database.tool_plain
async def query_database(query: str) -> list[dict[str, Any]]:
    """Run one read-only SQL query and return the rows it selects.

    Args:
        query: A single SELECT statement.
    """
    try:
        async with (
            async_readonly_connection() as conn,
            conn.cursor(row_factory=dict_row) as cursor,
        ):
            await cursor.execute(query)  # type: ignore[arg-type]
            if cursor.description is None:  # a statement with no result set
                return []
            rows = await cursor.fetchmany(MAX_ROWS + 1)
    except Exception as exc:  # bad SQL, a write, or the timeout: let the model fix it
        raise ModelRetry(f"Query failed: {exc}") from exc

    if len(rows) > MAX_ROWS:
        # Truncating silently would have the model answer from a partial table.
        raise ModelRetry(
            f"Query returned more than {MAX_ROWS} rows. Aggregate it in SQL "
            "(GROUP BY, SUM, date_trunc) or add a LIMIT."
        )
    return [{k: _jsonable(v) for k, v in row.items()} for row in rows]
