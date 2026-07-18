from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from db.models import Transaction
from db.session import async_session_maker

# Generated from the ORM model so the schema shown to the LLM never drifts.
DDL_TRANSACTION_TABLE = str(
    CreateTable(Transaction.__table__).compile(  # type: ignore[arg-type]
        dialect=postgresql.dialect()
    )
)


async def query_database_function(plan: str, query: str) -> str:
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                text(query), execution_options={"postgresql_readonly": True}
            )
            return str([dict(row) for row in result.mappings().all()])
    except Exception as e:
        return str(e)


query_function_description = (
    f"Run SQL query on transaction table {DDL_TRANSACTION_TABLE}"
)
