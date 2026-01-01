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
    PERSONAL_TRAVEL = "personal_travel"
    PERSONAL_ITEMS = "personal_items"
    SNACKS = "snacks"
    HEALTH = "health"

    OFFICE_COMMUTE = "office_commute"
    OFFICE_DAY_FOOD = "office_day_food"

    PHONE_BILL = "phone_bill"
    HOME_EXPENSES = "home_expenses"
    GOING_OUT_WITH_FRIENDS = "going_out_with_friends"

    UTILITIES = "utilities"
    GIFTS = "gifts"
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
