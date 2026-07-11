from sqlalchemy import text

from db.session import async_session_maker

DDL_TRANSACTION_TABLE = """\
CREATE TABLE public.transactions (
	amount float8 NOT NULL,
	title varchar(255) NOT NULL,
	description text NULL,
	is_expense bool NOT NULL,
	"date" timestamp NOT NULL,
	category varchar(50) NOT NULL,
	id uuid NOT NULL,
	created_at timestamp DEFAULT now() NOT NULL,
	updated_at timestamp NOT NULL,
	meta jsonb NULL,
	CONSTRAINT transactions_pkey PRIMARY KEY (id)
);
"""


async def query_database_function(plan: str, query: str) -> str:
    """Run SQL query on the transaction table
    {TABLE_SCHEMA}
    """.format(TABLE_SCHEMA=DDL_TRANSACTION_TABLE)
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
