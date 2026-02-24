from datetime import datetime
from zoneinfo import ZoneInfo

from agent.tools.query_database import (
    query_database_function,
    query_function_description,
)
from core.config import settings
from core.schema import ExpenseCategory, Transaction
from discord.message import Message
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.providers.mistral import MistralProvider
from services.db_proxy import db_proxy


def instructions() -> str:
    date_today = datetime.now(ZoneInfo("Asia/Kathmandu")).date()
    PROMPT = f"""\
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
        2. Call the `add_expense` tool with the extracted information.
        3. Call the `return_action` tool with success set to true and no reason.

Date Today: {date_today}
"""
    return PROMPT


class Context(BaseModel):
    message: Message
    send_final_response: bool = True

    class Config:
        arbitrary_types_allowed = True


model = MistralModel(
    "mistral-medium-2508", provider=MistralProvider(api_key=settings.MISTRAL_API_KEY)
)

finance_agent = Agent(
    model=model,
    instructions=instructions,
    deps_type=Context,
    tools=[
        Tool[Context](
            function=query_database_function,
            description=query_function_description,
            takes_ctx=False,
        )
    ],
    # retries=2
)


def date_from_string(date_str: str | None) -> datetime | None:
    NEPAL_TZ = ZoneInfo("Asia/Kathmandu")
    """Convert a date string in YYYY-MM-DD format to a timezone-aware datetime object (Nepal time)."""
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
        category: The category of the expense
        date: The date of the expense in YYYY-MM-DD format. Do not include the date if the expense is for today.
    """
    if not category:
        return "Invalid category provided."

    date_obj = date_from_string(date)
    if not date_obj:
        return "Invalid date format. Please use YYYY-MM-DD."

    expense = Transaction(
        amount=amount,
        date=date_obj,
        title=title,
        category=category,
        is_expense=True,
    )
    await db_proxy.add_transaction(expense)

    return f"Expense added: {expense.title} on {expense.date} for {expense.amount} in category {expense.category.value}."


@finance_agent.tool
async def end_action(
    ctx: RunContext[Context], *, success: bool, reason: str | None = None
) -> str:
    await ctx.deps.message.add_reaction("✅" if success else "❌")
    ctx.deps.send_final_response = False
    return "ended successfully"
