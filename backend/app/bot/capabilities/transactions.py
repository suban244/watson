import uuid

from pydantic_ai import Tool
from pydantic_ai.capabilities import Capability

from bot.tools.query_database import (
    query_database_function,
    query_function_description,
)
from db.session import async_session_maker
from schema.transaction import ExpenseCategory, IncomeCategory, TransactionCreate
from services import transactions as transaction_service
from datetime import datetime
from zoneinfo import ZoneInfo

from db.models import Transaction


def date_from_string(date_str: str | None) -> datetime | None:
    NEPAL_TZ = ZoneInfo("Asia/Kathmandu")
    try:
        if not date_str:
            return datetime.now(tz=NEPAL_TZ)
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=NEPAL_TZ)
    except ValueError:
        return None


def format_transaction(transaction: Transaction) -> str:
    kind = "expense" if transaction.is_expense else "income"
    return (
        f"- id={transaction.id} | {transaction.title} "
        f"| {transaction.date.date()} | {transaction.amount} NPR "
        f"| {transaction.category or 'N/A'} | {kind}"
    )



transactions = Capability(
    id="transactions",
    description="Record, search, and correct expenses and income.",
    instructions="""\
Transaction workflows:
1. Simple Expense Addition:
    - Trigger: User gives you a cost and a title of a expense.
    - User: "Add an expense of <amount> for food on <date>."
    - Steps:
        1. Parse the user's request to extract the amount, title, category(optional) and date (optional).
            - No need to ask for the date if not provided
            - If no category is clear from context, omit it (it will default to misc)
        2. Call the `add_expense` tool with the extracted information.
        3. Return Success as your response.

2. Income Addition:
    - Trigger: User mentions receiving money.
    - User: "Got my salary of <amount>", "Received <amount> from <source>."
    - Steps:
        1. Call the `add_income` tool with the extracted information.
        2. Return Success as your response.

3. Search / Query Expenses:
    - Trigger: User asks to find, look up, or list expenses matching a description.
    - User: "Find my food expenses", "What did I spend on transport last week?"
    - Steps:
        1. Use `search_expenses` for keyword-based lookups (title/description matching).
        2. Use `list_recent_transactions` for "recent" / "last N" style requests.
        3. Use `query_database` for date-filtered or aggregate queries (totals, counts, date ranges).
        4. Return the answer as a text response, never Success.

4. Corrections:
    - Trigger: User wants to fix or remove a transaction.
    - User: "That was 400, not 500", "Delete that last one", "That lunch was actually snacks."
    - Steps:
        1. Find the transaction id using `list_recent_transactions` or `search_expenses`
           (use the conversation context to pick the right one).
        2. Call `update_transaction` or `delete_transaction` with that id.
        3. Return Success as your response.
""",
    tools=[
        Tool(
            function=query_database_function,
            description=query_function_description,
            takes_ctx=False,
        )
    ],
)


@transactions.tool_plain
async def add_expense(
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

    date_obj = date_from_string(date)
    if not date_obj:
        return "Invalid date format. Please use YYYY-MM-DD."

    expense = TransactionCreate(
        amount=amount,
        date=date_obj,
        title=title,
        category=category,
        is_expense=True,
    )
    async with async_session_maker() as session:
        trnsaction = await transaction_service.create_transaction(session, expense)
        transaction_id = trnsaction.id
    return f"Expense added: {title} on {date_obj.date()} for {amount} in category {category.value}. Trnsaction ID: {transaction_id}."


@transactions.tool_plain
async def add_income(
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

    date_obj = date_from_string(date)
    if not date_obj:
        return "Invalid date format. Please use YYYY-MM-DD."

    income = TransactionCreate(
        amount=amount,
        date=date_obj,
        title=title,
        category=category,
        is_expense=False,
    )
    async with async_session_maker() as session:
        await transaction_service.create_transaction(session, income)
    return f"Income added: {title} on {date_obj.date()} for {amount} in category {category.value}."


@transactions.tool_plain
async def search_expenses(search_query: str) -> str:
    """Search for expenses in the database based on a query string.
    Args:
        search_query: A string to search for in the title or description of expenses (e.g., "food", "transport").
    """
    async with async_session_maker() as session:
        results = await transaction_service.search_transactions(
            session, search_query, limit=20
        )
    if not results:
        return "No expenses found matching your query."

    response = "Search results:\n"
    for expense in results:
        response += format_transaction(expense) + "\n"
    return response


@transactions.tool_plain
async def list_recent_transactions(limit: int = 10) -> str:
    """List the most recently added transactions, newest first.
    Use this to find a transaction the user wants to correct or delete.
    Args:
        limit: Maximum number of transactions to return (default 10).
    """
    async with async_session_maker() as session:
        results = await transaction_service.list_transactions(session, limit=limit)
    if not results:
        return "No transactions found."

    response = "Most recently added transactions (newest first):\n"
    for transaction in results:
        response += format_transaction(transaction) + "\n"
    return response


@transactions.tool_plain
async def update_transaction(
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

    updates: dict = {
        key: value
        for key, value in {
            "title": title,
            "amount": amount,
            "category": category,
        }.items()
        if value is not None
    }
    if date is not None:
        date_obj = date_from_string(date)
        if not date_obj:
            return "Invalid date format. Please use YYYY-MM-DD."
        updates["date"] = date_obj

    async with async_session_maker() as session:
        updated = await transaction_service.update_transaction(
            session, parsed_id, updates
        )
    if updated is None:
        return "Transaction not found."
    return f"Transaction updated:\n{format_transaction(updated)}"


@transactions.tool_plain
async def delete_transaction(transaction_id: str) -> str:
    """Delete a transaction from the database.
    Args:
        transaction_id: The id of the transaction to delete (from search or list results).
    """
    try:
        parsed_id = uuid.UUID(transaction_id)
    except ValueError:
        return "Invalid transaction id."

    async with async_session_maker() as session:
        deleted = await transaction_service.delete_transaction(session, parsed_id)
    if not deleted:
        return "Transaction not found."
    return "Transaction deleted."
