"""Budget aggregates: pot spend against pot limits, and monthly spend against
the standard budget.

Aggregates in SQL rather than pulling rows into Python — the transaction table
is the one that grows, and this runs on a Pi.

Two time scales live here: pot spend is all-time (pots are themes and events,
not recurring budgets), while envelopes are calendar-scoped via `month_bounds`.
Reads never write.
"""

from datetime import date

from sqlalchemy import Text, and_, case, cast, func, literal, select
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import MonthlyBudget, Tag, TagStatus, Transaction
from schema.budget import (
    DEFAULT_OVERALL_LIMIT,
    BudgetOverview,
    BudgetSource,
    EnvelopeStatus,
    MonthlyBudgetStatus,
    PotSummary,
    default_limits,
)
from schema.tag import TagRead
from utils.timezone import month_bounds, month_start, next_month_start


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
                # `tags.slug` is String(50), so cast — `text[] @> varchar[]`
                # has no operator.
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


async def get_monthly_override(
    session: AsyncSession, month: date
) -> MonthlyBudget | None:
    return await session.get(MonthlyBudget, month_start(month))


async def ensure_monthly_budget(
    session: AsyncSession, month: date
) -> MonthlyBudget | None:
    """Persist the month's budget the first time it is needed, so a later change
    to the code template cannot rewrite what a month was budgeted at.

    Future months are left unmaterialised — pinning them early would freeze
    them to today's template before that template is the one you mean.
    """
    start = month_start(month)
    budget = await session.get(MonthlyBudget, start)
    if budget is not None or start > month_start():
        return budget

    budget = MonthlyBudget(
        month=start, limits=default_limits(), overall_limit=DEFAULT_OVERALL_LIMIT
    )
    session.add(budget)
    try:
        await session.commit()
    except IntegrityError:
        # Another request materialised it first.
        await session.rollback()
        return await session.get(MonthlyBudget, start)

    await session.refresh(budget)
    return budget


async def resolve_limits(
    session: AsyncSession, month: date
) -> tuple[dict[str, float], float | None, BudgetSource]:
    budget = await ensure_monthly_budget(session, month)
    if budget is None:
        return default_limits(), DEFAULT_OVERALL_LIMIT, "standard"

    limits = dict(budget.limits)
    source: BudgetSource = (
        "standard"
        if limits == default_limits() and budget.overall_limit == DEFAULT_OVERALL_LIMIT
        else "override"
    )
    return limits, budget.overall_limit, source


async def _excluded_pot_slugs(session: AsyncSession) -> list[str]:
    """Archived pots still count, so archiving never rewrites a past month."""
    result = await session.execute(
        select(Tag.slug).where(Tag.is_pot.is_(True), Tag.exclude_from_monthly.is_(True))
    )
    return list(result.scalars().all())


async def _spend_by_category(
    session: AsyncSession, month: date, excluded_slugs: list[str]
) -> dict[str | None, tuple[float, float]]:
    """Per-category `(spent, excluded_spent)` for the month, keyed by category
    with `None` for uncategorized."""
    start, end = month_bounds(month)

    if excluded_slugs:
        excluded_total = func.sum(
            case(
                (Transaction.tags.overlap(excluded_slugs), Transaction.amount),
                else_=0.0,
            )
        )
    else:
        excluded_total = literal(0.0)

    query = (
        select(Transaction.category, func.sum(Transaction.amount), excluded_total)
        .where(
            Transaction.is_expense.is_(True),
            Transaction.date >= start,
            Transaction.date < end,
        )
        .group_by(Transaction.category)
    )
    result = await session.execute(query)
    return {
        category: (float(total), float(excluded))
        for category, total, excluded in result.all()
    }


async def monthly_status(
    session: AsyncSession, month: date | None = None
) -> MonthlyBudgetStatus:
    start = month_start(month)

    limits, overall_limit, source = await resolve_limits(session, start)
    excluded_slugs = await _excluded_pot_slugs(session)
    spend = await _spend_by_category(session, start, excluded_slugs)

    # Untouched envelopes are listed at zero so the page shows the whole budget.
    envelopes = [
        EnvelopeStatus(
            category=category,
            limit=limit,
            spent=spend.get(category, (0.0, 0.0))[0],
            excluded_spent=spend.get(category, (0.0, 0.0))[1],
        )
        for category, limit in sorted(limits.items())
    ]

    # Spend in a category with no envelope would otherwise be invisible.
    # `None` is filtered before sorting: it is uncategorized spend, reported
    # separately, and would not compare against the str keys.
    unbudgeted = sorted(
        (category, totals)
        for category, totals in spend.items()
        if category is not None and category not in limits
    )
    envelopes += [
        EnvelopeStatus(
            category=category, limit=0.0, spent=total, excluded_spent=excluded
        )
        for category, (total, excluded) in unbudgeted
    ]

    gross = sum(total for total, _ in spend.values())
    excluded_total = sum(excluded for _, excluded in spend.values())
    uncategorized, uncategorized_excluded = spend.get(None, (0.0, 0.0))

    return MonthlyBudgetStatus(
        month_start=start,
        month_end=next_month_start(start),
        source=source,
        gross_spend=gross,
        excluded_spend=excluded_total,
        net_spend=gross - excluded_total,
        uncategorized_spend=uncategorized,
        uncategorized_excluded_spend=uncategorized_excluded,
        overall_limit=overall_limit,
        envelopes=envelopes,
    )


async def set_monthly_budget(
    session: AsyncSession, month: date, updates: dict
) -> MonthlyBudget:
    """Override a month's budget, seeding from the standard so a partial edit
    does not wipe the rest."""
    start = month_start(month)
    budget = await ensure_monthly_budget(session, start)

    if budget is None:
        # A future month, which `ensure_monthly_budget` leaves alone until it
        # arrives. Editing one deliberately is fine, so create it here.
        budget = MonthlyBudget(
            month=start, limits=default_limits(), overall_limit=DEFAULT_OVERALL_LIMIT
        )
        session.add(budget)

    if updates.get("limits") is not None:
        budget.limits = dict(updates["limits"])
    if "overall_limit" in updates:
        budget.overall_limit = updates["overall_limit"]

    await session.commit()
    await session.refresh(budget)
    return budget


async def clear_monthly_budget(session: AsyncSession, month: date) -> bool:
    """Drop a month's override so it follows the standard budget again."""
    override = await get_monthly_override(session, month)
    if override is None:
        return False
    await session.delete(override)
    await session.commit()
    return True


async def overview(session: AsyncSession, month: date | None = None) -> BudgetOverview:
    return BudgetOverview(
        pots=await pot_summaries(session),
        month=await monthly_status(session, month),
    )
