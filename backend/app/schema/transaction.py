from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class IncomeCategory(StrEnum):
    SALARY = "salary"

    @classmethod
    def from_string(cls, value: str) -> "IncomeCategory | None":
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
        try:
            return cls(value)
        except ValueError:
            return None


class Transaction(BaseModel):
    amount: float
    title: str
    description: str | None = None
    is_expense: bool = True
    date: datetime

    category: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(Transaction):
    pass


class TransactionRead(Transaction):
    id: UUID
    pass


class TransactionUpdate(BaseModel):
    amount: float | None = None
    title: str | None = None
    description: str | None = None
    is_expense: bool | None = None
    date: datetime | None = None

    category: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TransactionSearch(BaseModel):
    search_query: str
