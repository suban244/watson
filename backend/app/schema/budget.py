"""Budget schemas and the standard monthly budget.

The standard budget lives in code; a month can override it through the API,
which writes a `MonthlyBudget` row that shadows the standard for that month.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from schema.tag import TagRead
from schema.transaction import ExpenseCategory

# Per-category limits in NPR, used by every month without an override.
# Changing these changes every such month, past ones included.
DEFAULT_MONTHLY_LIMITS: dict[ExpenseCategory, float] = {
    ExpenseCategory.GROCERIES: 2000,
    ExpenseCategory.HOUSEHOLD: 2000,
    ExpenseCategory.DINING_OUT: 2000,
    ExpenseCategory.EXPERIENCES: 4000,
    ExpenseCategory.SNACKS: 2000,
    ExpenseCategory.SUBSCRIPTIONS: 2000,
    ExpenseCategory.TRANSPORT: 2000,
    ExpenseCategory.GIFTS: 2000,
    ExpenseCategory.MISC: 2000,
}

DEFAULT_OVERALL_LIMIT: float | None = 2000

BudgetSource = Literal["standard", "override"]


def default_limits() -> dict[str, float]:
    return {
        category.value: amount for category, amount in DEFAULT_MONTHLY_LIMITS.items()
    }


class PotSummary(TagRead):
    """A pot plus what it has spent, all-time."""

    spent: float
    transaction_count: int


class EnvelopeStatus(BaseModel):
    category: str
    limit: float
    spent: float
    excluded_spent: float


class MonthlyBudgetStatus(BaseModel):
    month_start: date
    month_end: date  # exclusive
    source: BudgetSource

    gross_spend: float
    excluded_spend: float
    net_spend: float

    uncategorized_spend: float
    uncategorized_excluded_spend: float

    overall_limit: float | None
    envelopes: list[EnvelopeStatus]


class BudgetOverview(BaseModel):
    pots: list[PotSummary]
    month: MonthlyBudgetStatus


class MonthlyBudgetUpdate(BaseModel):
    """Dump with `exclude_unset=True` so an explicit `overall_limit: null`
    clears the cap rather than reading as "unchanged"."""

    limits: dict[str, float] | None = Field(
        default=None, description="Replaces the month's limits wholesale."
    )
    overall_limit: float | None = None

    model_config = ConfigDict(extra="forbid")
