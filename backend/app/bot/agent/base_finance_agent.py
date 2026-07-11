import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

import discord

from bot.agent.tools.query_database import (
    query_database_function,
    query_function_description,
)
from bot.services.db_service import db_service
from bot.schema import DiscordTransaction
from config import settings
from schema.transaction import ExpenseCategory, IncomeCategory


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
        3. Call the `end_action` tool with success set to true and no reason.

2. Income Addition:
    - Trigger: User mentions receiving money.
    - User: "Got my salary of <amount>", "Received <amount> from <source>."
    - Steps:
        1. Call the `add_income` tool with the extracted information.
        2. Call the `end_action` tool with success set to true.

3. Search / Query Expenses:
    - Trigger: User asks to find, look up, or list expenses matching a description.
    - User: "Find my food expenses", "What did I spend on transport last week?"
    - Steps:
        1. Use `search_expenses` for keyword-based lookups (title/description matching).
        2. Use `list_recent_transactions` for "recent" / "last N" style requests.
        3. Use `query_database` for date-filtered or aggregate queries (totals, counts, date ranges).
        4. Answer the user directly in your final response. Do NOT call `end_action` for questions.

4. Corrections:
    - Trigger: User wants to fix or remove a transaction.
    - User: "That was 400, not 500", "Delete that last one", "That lunch was actually snacks."
    - Steps:
        1. Find the transaction id using `list_recent_transactions` or `search_expenses`
           (use the conversation context to pick the right one).
        2. Call `update_transaction` or `delete_transaction` with that id.
        3. Call the `end_action` tool with success set to true.

Rules:
- Never show raw transaction ids to the user; they are for tool calls only.
- If a step fails, call `end_action` with success set to false and explain what went wrong in your final response.

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


def _format_transaction(transaction: dict) -> str:
    kind = "expense" if transaction.get("is_expense", True) else "income"
    return (
        f"- id={transaction['id']} | {transaction['title']} "
        f"| {transaction['date'][:10]} | {transaction['amount']} NPR "
        f"| {transaction.get('category') or 'N/A'} | {kind}"
    )


@finance_agent.tool
async def add_income(
    ctx: RunContext[Context],
    title: str,
    amount: float,
    category: IncomeCategory | None = None,
    date: str | None = None,
) -> str:
    """Add an income entry to the database.
    Args:
        title: A brief description of the income (e.g., "Monthly salary").
        amount: The amount received in NPR (e.g., 50000.0).
        category: The category of the income. Omit if unclear (defaults to salary).
        date: The date of the income in YYYY-MM-DD format. Omit if it is for today.
    """
    if not category:
        category = IncomeCategory.SALARY

    date_obj = _date_from_string(date)
    if not date_obj:
        return "Invalid date format. Please use YYYY-MM-DD."

    income = DiscordTransaction(
        amount=amount,
        date=date_obj,
        title=title,
        category=category,
        is_expense=False,
    )
    await db_service.add_transaction(income)
    return f"Income added: {income.title} on {income.date} for {income.amount} in category {income.category.value}."


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
        response += _format_transaction(expense) + "\n"
    return response


@finance_agent.tool
async def list_recent_transactions(ctx: RunContext[Context], limit: int = 10) -> str:
    """List the most recently added transactions, newest first.
    Use this to find a transaction the user wants to correct or delete.
    Args:
        limit: Maximum number of transactions to return (default 10).
    """
    results = await db_service.list_recent_transactions(limit=limit)
    if not results:
        return "No transactions found."

    response = "Most recently added transactions (newest first):\n"
    for transaction in results:
        response += _format_transaction(transaction) + "\n"
    return response


@finance_agent.tool
async def update_transaction(
    ctx: RunContext[Context],
    transaction_id: str,
    title: str | None = None,
    amount: float | None = None,
    category: ExpenseCategory | IncomeCategory | None = None,
    date: str | None = None,
) -> str:
    """Update fields of an existing transaction. Only provided fields are changed.
    Args:
        transaction_id: The id of the transaction to update (from search or list results).
        title: New title, if it should change.
        amount: New amount in NPR, if it should change.
        category: New category, if it should change.
        date: New date in YYYY-MM-DD format, if it should change.
    """
    try:
        parsed_id = uuid.UUID(transaction_id)
    except ValueError:
        return "Invalid transaction id."

    update_data: dict = {"title": title, "amount": amount, "category": category}
    if date is not None:
        date_obj = _date_from_string(date)
        if not date_obj:
            return "Invalid date format. Please use YYYY-MM-DD."
        update_data["date"] = date_obj

    updated = await db_service.update_transaction(parsed_id, update_data)
    if updated is None:
        return "Transaction not found."
    return f"Transaction updated:\n{_format_transaction(updated)}"


@finance_agent.tool
async def delete_transaction(ctx: RunContext[Context], transaction_id: str) -> str:
    """Delete a transaction from the database.
    Args:
        transaction_id: The id of the transaction to delete (from search or list results).
    """
    try:
        parsed_id = uuid.UUID(transaction_id)
    except ValueError:
        return "Invalid transaction id."

    status = await db_service.delete_transaction(parsed_id)
    if status == 404:
        return "Transaction not found."
    return "Transaction deleted."


@finance_agent.tool
async def end_action(
    ctx: RunContext[Context], *, success: bool, reason: str | None = None
) -> str:
    """Signal the end of an action (add/update/delete) and whether it was successful.
    Do not call this when answering a question."""
    await ctx.deps.message.add_reaction("✅" if success else "❌")
    # On failure the final response is still sent so the user learns what went wrong.
    ctx.deps.send_final_response = not success
    return "ended successfully"
