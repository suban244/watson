from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

import discord

from bot.agent.tools.query_database import query_database_function, query_function_description
from bot.services.db_service import db_service
from bot.schema import DiscordTransaction
from config import settings
from schema.transaction import ExpenseCategory


def instructions() -> str:
    date_today = datetime.now(ZoneInfo("Asia/Kathmandu")).date()
    return f"""\
You are a finance agent that helps users manage their expenses.
The currency is NPR (Nepalese Rupee).

Domain Keywords:
Pathao: (a ride-hailing service in Nepal)

Here is your workflow for basic actions
1. Simple Expense Addition:
    - Trigger: User gives you a cost and a title of a expense.
    - User: "Add an expense of <amount> for food on <date>."
    - Steps:
        1. Parse the user's request to extract the amount, title, category(optional) and date (optional).
            - No need to ask for the date if not provided
            - If no category is clear from context, omit it (it will default to misc)
        2. Call the `add_expense` tool with the extracted information.
        3. Call the `return_action` tool with success set to true and no reason.

2. Search / Query Expenses:
    - Trigger: User asks to find, look up, or list expenses matching a description.
    - User: "Find my food expenses", "What did I spend on transport last week?"
    - Steps:
        1. Use `search_expenses` for keyword-based lookups (title/description matching).
        2. Use `query_database` for date-filtered or aggregate queries (totals, counts, date ranges).
        3. Call the `return_action` tool with success set to true.

Date Today: {date_today}
"""


class Context(BaseModel):
    message: discord.Message
    send_final_response: bool = True

    model_config = {"arbitrary_types_allowed": True}


def _make_model() -> OpenRouterModel:
    return OpenRouterModel(
        model_name="openai/gpt-oss-120b",
        provider=OpenRouterProvider(api_key=settings.OPENROUTER_API_KEY),
    )


finance_agent = Agent(
    model=_make_model(),
    instructions=instructions,
    deps_type=Context,
    tools=[
        Tool[Context](
            function=query_database_function,
            description=query_function_description,
            takes_ctx=False,
        )
    ],
)


def _date_from_string(date_str: str | None) -> datetime | None:
    NEPAL_TZ = ZoneInfo("Asia/Kathmandu")
    try:
        if not date_str:
            return datetime.now(tz=NEPAL_TZ)
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=NEPAL_TZ)
    except ValueError:
        return None


@finance_agent.tool
async def add_expense(
    ctx: RunContext[Context],
    title: str,
    amount: float,
    category: ExpenseCategory | None = None,
    date: str | None = None,
) -> str:
    """Add an expense to the database.
    Args:
        title: A brief description of the expense (e.g., "Lunch at cafe").
        amount: The cost of the expense in NPR (e.g., 500.0).
        category: The category of the expense.
        date: The date of the expense in YYYY-MM-DD format. Omit if the expense is for today.
    """
    if not category:
        category = ExpenseCategory.MISC

    date_obj = _date_from_string(date)
    if not date_obj:
        return "Invalid date format. Please use YYYY-MM-DD."

    expense = DiscordTransaction(
        amount=amount,
        date=date_obj,
        title=title,
        category=category,
        is_expense=True,
    )
    await db_service.add_transaction(expense)
    return f"Expense added: {expense.title} on {expense.date} for {expense.amount} in category {expense.category.value}."


@finance_agent.tool
async def search_expenses(ctx: RunContext[Context], search_query: str) -> str:
    """Search for expenses in the database based on a query string.
    Args:
        search_query: A string to search for in the title or description of expenses (e.g., "food", "transport").
    """
    results = await db_service.search_transactions(search_query)
    if not results:
        return "No expenses found matching your query."

    response = "Search results:\n"
    for expense in results:
        response += f"- {expense['title']} on {expense['date'][:10]} for {expense['amount']} in category {expense.get('category', 'N/A')}\n"
    return response


@finance_agent.tool
async def end_action(
    ctx: RunContext[Context], *, success: bool, reason: str | None = None
) -> str:
    """Signal the end of the action and whether it was successful."""
    await ctx.deps.message.add_reaction("✅" if success else "❌")
    ctx.deps.send_final_response = False
    return "ended successfully"
