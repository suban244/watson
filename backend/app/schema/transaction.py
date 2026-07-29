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
    """Expense categories. Each member carries a human/LLM-facing description so
    the value and its purpose stay in one place; `reference()` renders them for
    the bot's instructions."""

    description: str

    def __new__(cls, value: str, description: str = "") -> "ExpenseCategory":
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.description = description
        return obj

    GROCERIES = "groceries", "Food and drink bought to prepare or eat at home."
    SNACKS = "snacks", "Food and drink bought for snacking (chips, icecream, etc.)."
    DINING_OUT = "dining_out", "Meals, snacks or coffee bought and eaten outside home."
    TRANSPORT = "transport", "Day-to-day rides, fuel and fares for getting around."
    TRAVEL = "travel", "Multi-day trips and vacations (fares, lodging, etc.)."
    GOING_OUT = (
        "going_out",
        "Casual social hangouts with friends (drinks, dinners) — defined by the company.",
    )
    EXPERIENCES = (
        "experiences",
        "Paid activities, events and hobbies defined by the activity itself (concerts, tickets, climbing, workshops), solo or not.",
    )
    HEALTH = "health", "Medicine, doctor or dental visits, fitness and wellness."
    EDUCATION = "education", "Courses, books, certifications and tuition."
    UTILITIES = (
        "utilities",
        "Recurring home services — electricity, water, phone, internet.",
    )
    SUBSCRIPTIONS = (
        "subscriptions",
        "Recurring digital services and memberships (streaming, software, apps).",
    )
    HOUSEHOLD = (
        "household",
        "Home supplies and costs — toiletries, cleaning, kitchenware, rent, maintenance.",
    )
    PERSONAL_ITEMS = (
        "personal_items",
        "Things for yourself — clothing, grooming, gadgets, accessories.",
    )
    GIFTS = "gifts", "Presents for a person or occasion (birthday, wedding)."
    FAMILY = "family", "Money given to parents, siblings or relatives as support."
    MISC = "misc", "Anything that doesn't fit another category."

    @classmethod
    def from_string(cls, value: str) -> "ExpenseCategory | None":
        try:
            return cls(value)
        except ValueError:
            return None

    @classmethod
    def reference(cls) -> str:
        """Render `- value: description` lines for the bot's instructions."""
        return "\n".join(f"- {m.value}: {m.description}" for m in cls)


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


class CategoryOptions(BaseModel):
    expense: list[str]
    income: list[str]
