from services.db_proxy import db_proxy

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
    """Run Sql query on the transaction table
    {TABLE_SCHEMA}
    """.format(TABLE_SCHEMA=DDL_TRANSACTION_TABLE)
    try:
        result = await db_proxy.run_sql(query)
        return result
    except Exception as e:
        return str(e)


query_function_description = (
    f"Run SQL query on transaction table {DDL_TRANSACTION_TABLE}"
)
