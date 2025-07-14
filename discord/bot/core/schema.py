from pydantic import BaseModel, Field
from enum import StrEnum
import datetime


class IncomeCategory(StrEnum):
    SALARY = "salary"

    @classmethod
    def from_string(cls, value: str) -> "IncomeCategory | None":
        """Convert a string to an IncomeCategory enum."""
        try:
            return cls(value)
        except ValueError:
            return None


class ExpenseCategory(StrEnum):
    HOME_EXPENSES = "home_expenses"
    OFFICE_COMMUTE = "office_commute"
    PERSONAL_TRAVEL = "personal_travel"
    OFFICE_DAY_SNACKS = "office_day_snacks"
    EATING_OUT_WITH_FRIENDS = "eating_out_with_friends"
    MISC = "misc"

    @classmethod
    def from_string(cls, value: str) -> "ExpenseCategory | None":
        """Convert a string to an ExpenseCategory enum."""
        try:
            return cls(value)
        except ValueError:
            return None


class Transaction(BaseModel):
    amount: float = Field(..., description="Amount of the Transaction")
    title: str = Field(..., description="Title of the Transaction")
    description: str | None = Field(
        default=None, description="Description of the Transaction"
    )
    date: datetime.datetime = Field(
        ..., description="Date of the expense in YYYY-MM-DD format"
    )
    category: ExpenseCategory | IncomeCategory = Field(
        ..., description="Category of the Transaction"
    )
    is_expense: bool = Field(
        default=True, description="True if this is an expense, False if it's income"
    )

    def to_sheet_row(self) -> list[str | int | float]:
        """Convert the expense to a list suitable for appending to a sheet."""
        return [
            self.date.strftime("%m/%d/%Y"),
            self.title,
            self.category.value,
            self.amount,
        ]
