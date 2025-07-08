from agent.schema.base import FunctionTool, ToolResponse, ParameterData
from core.schema import ExpenseCategory, Expense
from datetime import datetime
from services.sheet import expense_sheet

from datetime import date


def date_from_string(date_str: str | None) -> date | None:
    """Convert a date string in YYYY-MM-DD format to a date object."""
    try:
        if not date_str:
            return datetime.now().date()
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


async def add_expense_function(
    title: str,
    amount: float,
    category: str | None = None,
    date: str | None = None,
    **kwargs,
) -> ToolResponse:
    expense_category = ExpenseCategory.from_string(category) if category else None
    if not expense_category:
        return ToolResponse(content="Invalid category provided.")

    date_obj = date_from_string(date)
    if not date_obj:
        return ToolResponse(content="Invalid date format. Please use YYYY-MM-DD.")

    expense = Expense(
        date=date_obj,
        title=title,
        amount=amount,
        category=expense_category,
    )
    expense_sheet.append_row(expense)

    return ToolResponse(
        content=f"Expense added: {expense.title} on {expense.date} for {expense.amount} in category {expense.category.value}."
    )


add_expense = FunctionTool(
    name="add_expense",
    description="Add an expense to the budget.",
    parameters={
        "title": ParameterData(type="string", description="The title of the expense."),
        "amount": ParameterData(
            type="number", description="The amount of the expense."
        ),
        "category": ParameterData(
            type="string",
            description="The category of the expense. Must be one of: "
            + ", ".join([cat.value for cat in ExpenseCategory]),
            required=False,
        ),
        "date": ParameterData(
            type="string",
            description="The date of the expense in YYYY-MM-DD format. Skip if not specified.",
            required=False,
        ),
    },
    target_function=add_expense_function,
)
