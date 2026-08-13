"""Budget aggregates: what each pot has spent against its limit, and the monthly
figure that `exclude_from_monthly` is meant to adjust.

Everything here aggregates in SQL rather than pulling rows into Python. The
transaction table is the one that grows without bound, and this runs on a Pi —
summing 5,000 rows in Postgres costs a scan; shipping them to the client costs
memory twice.

Pot spend is all-time, not per-period: `Tag` carries no period column, and pots
are framed as themes or events ("Fifa Final 2026") rather than recurring budgets.
The monthly figures below are the only calendar-scoped numbers.
"""

from datetime import date

from sqlalchemy import Text, and_, cast, func, select
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Tag, TagStatus, Transaction
from schema.tag import BudgetOverview, MonthlySummary, PotSummary, TagRead


async def pot_summaries(session: AsyncSession) -> list[PotSummary]:
    """Active pots with their spend to date.

    A LEFT JOIN rather than a filter, so a pot that has never been applied to
    anything still comes back at zero instead of vanishing from the page.
    """
    query = (
        select(
            Tag,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("spent"),
            func.count(Transaction.id).label("transaction_count"),
        )
        .select_from(Tag)
        .outerjoin(
            Transaction,
            and_(
                # `@> ARRAY[tags.slug]`, served by the GIN index on transactions.tags.
                # `tags.slug` is String(50), so cast — `text[] @> varchar[]` has no operator.
                Transaction.tags.contains(array([cast(Tag.slug, Text)])),
                Transaction.is_expense.is_(True),
            ),
        )
        .where(Tag.is_pot.is_(True), Tag.status == TagStatus.ACTIVE)
        .group_by(Tag.id)
        .order_by(Tag.name)
    )

    result = await session.execute(query)
    return [
        PotSummary(
            **TagRead.model_validate(tag).model_dump(),
            spent=float(spent),
            transaction_count=count,
        )
        for tag, spent, count in result.all()
    ]


async def monthly_summary(
    session: AsyncSession, *, today: date | None = None
) -> MonthlySummary:
    """Calendar-month expenses, split by whether a pot has opted out.

    `exclude_from_monthly` marks a pot whose spending is a one-off that would
    distort the monthly picture — a wedding, a flight. `net_spend` is the number
    to read as "normal" spending for the month.
    """
    month_start = (today or date.today()).replace(day=1)
    in_month = and_(Transaction.is_expense.is_(True), Transaction.date >= month_start)

    total = func.coalesce(func.sum(Transaction.amount), 0.0)
    gross = (await session.execute(select(total).where(in_month))).scalar_one()

    excluded_slugs = (
        (
            await session.execute(
                select(Tag.slug).where(
                    Tag.is_pot.is_(True), Tag.exclude_from_monthly.is_(True)
                )
            )
        )
        .scalars()
        .all()
    )

    excluded = 0.0
    if excluded_slugs:
        excluded = (
            await session.execute(
                select(total).where(
                    in_month, Transaction.tags.overlap(list(excluded_slugs))
                )
            )
        ).scalar_one()

    return MonthlySummary(
        month_start=month_start,
        gross_spend=float(gross),
        excluded_spend=float(excluded),
        net_spend=float(gross) - float(excluded),
    )


async def overview(session: AsyncSession) -> BudgetOverview:
    return BudgetOverview(
        pots=await pot_summaries(session),
        month=await monthly_summary(session),
    )
