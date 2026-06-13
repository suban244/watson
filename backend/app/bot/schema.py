import datetime

from pydantic import BaseModel, Field

from schema.transaction import ExpenseCategory, IncomeCategory


class DiscordTransaction(BaseModel):
    amount: float = Field(..., description="Amount of the Transaction")
    title: str = Field(..., description="Title of the Transaction")
    description: str | None = Field(default=None, description="Description of the Transaction")
    date: datetime.datetime = Field(..., description="Date of the expense in YYYY-MM-DD format")
    category: ExpenseCategory | IncomeCategory = Field(..., description="Category of the Transaction")
    is_expense: bool = Field(default=True, description="True if this is an expense, False if it's income")
