from agent.schema.base import FunctionTool, ToolResponse, ParameterData
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


async def query_database_function(plan: str, query: str, **kwargs) -> ToolResponse:
    try:
        result = await db_proxy.run_sql(query)
        return ToolResponse(content=result)
    except Exception as e:
        return ToolResponse(content=f"Error executing query: {str(e)}")


query_database = FunctionTool(
    name="query_database",
    description=f"Run SQL queries on the data base. Here are the different tables available to you:  \n{DDL_TRANSACTION_TABLE}\n ",
    parameters={
        "query": ParameterData(type="string", description="The SQL query to execute."),
        "plan": ParameterData(
            type="string",
            description="Think about the query and plan it before executing.",
        ),
    },
    strict_config=False,
    target_function=query_database_function,
)
