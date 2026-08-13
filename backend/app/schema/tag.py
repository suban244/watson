from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TagBase(BaseModel):
    name: str
    description: str | None = None

    is_pot: bool = False
    # Both are only meaningful on a pot; the service rejects them otherwise.
    exclude_from_monthly: bool = False
    limit_amount: float | None = None


class TagCreate(TagBase):
    # Derived from `name` when omitted. Immutable once the tag exists.
    slug: str | None = None


class TagRead(TagBase):
    id: UUID
    slug: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class PotSummary(TagRead):
    """A pot plus what it has spent, all-time. `limit_amount` is inherited and
    may be null, meaning the pot tracks spend without a target."""

    spent: float
    transaction_count: int


class MonthlySummary(BaseModel):
    month_start: date
    gross_spend: float
    #: Spend attributed to pots flagged `exclude_from_monthly`.
    excluded_spend: float
    #: `gross_spend` minus `excluded_spend` — the month's "normal" spending.
    net_spend: float


class BudgetOverview(BaseModel):
    pots: list[PotSummary]
    month: MonthlySummary


class TagUpdate(BaseModel):
    """Callers should dump with `exclude_unset=True` so that explicitly passing
    `limit_amount: null` clears the limit, rather than being read as "unchanged".

    `slug` and `status` are absent by design: slugs are immutable, and status
    moves through `archive_tag` / `restore_tag`.
    """

    name: str | None = None
    description: str | None = None
    is_pot: bool | None = None
    exclude_from_monthly: bool | None = None
    limit_amount: float | None = None
