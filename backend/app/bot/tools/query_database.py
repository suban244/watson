from psycopg.rows import dict_row
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from db.models import Transaction
from db.readonly import async_readonly_connection

# Generated from the ORM model so the schema shown to the LLM never drifts.
DDL_TRANSACTION_TABLE = str(
    CreateTable(Transaction.__table__).compile(  # type: ignore[arg-type]
        dialect=postgresql.dialect()
    )
)


async def query_database_function(plan: str, query: str) -> str:
    try:
        async with async_readonly_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query)  # type: ignore[arg-type]
                return str(await cursor.fetchall())
    except Exception as e:
        return str(e)


query_function_description = (
    f"Run SQL query on transaction table {DDL_TRANSACTION_TABLE}\n"
    "`tags` is a text[] of tag slugs: match it with `'slug' = ANY(tags)` or "
    "`tags @> ARRAY['slug']`, never with `=`.\n"
    "The connection is read-only and times out after 10s, so write only "
    "SELECT statements and keep aggregates indexed."
)
