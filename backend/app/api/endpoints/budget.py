from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from api.deps import SessionDep
from schema.budget import BudgetOverview, MonthlyBudgetStatus, MonthlyBudgetUpdate
from services import budget as budget_service
from utils.timezone import month_start, parse_month_key

router = APIRouter()

MonthQuery = Annotated[
    str | None, Query(description="Month as YYYY-MM; defaults to now")
]


def parse_month(value: str | None) -> date:
    """Accept `YYYY-MM` (or a full `YYYY-MM-DD`) and snap to the 1st."""
    if value is None:
        return month_start()
    try:
        return parse_month_key(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="month must be YYYY-MM") from exc


@router.get("/overview/", response_model=BudgetOverview)
async def get_overview(session: SessionDep, month: MonthQuery = None):
    """Active pots with their spend to date, plus the month's envelope status."""
    return await budget_service.overview(session, parse_month(month))


@router.get("/monthly/", response_model=MonthlyBudgetStatus)
async def get_monthly(session: SessionDep, month: MonthQuery = None):
    return await budget_service.monthly_status(session, parse_month(month))


@router.patch("/monthly/", response_model=MonthlyBudgetStatus)
async def update_monthly(
    budget_update: MonthlyBudgetUpdate,
    session: SessionDep,
    month: MonthQuery = None,
):
    """Override the standard budget for this month."""
    target = parse_month(month)
    await budget_service.set_monthly_budget(
        session, target, budget_update.model_dump(exclude_unset=True)
    )
    return await budget_service.monthly_status(session, target)


@router.delete("/monthly/", response_model=MonthlyBudgetStatus)
async def clear_monthly(session: SessionDep, month: MonthQuery = None):
    """Drop this month's override so it follows the standard budget again."""
    target = parse_month(month)
    await budget_service.clear_monthly_budget(session, target)
    return await budget_service.monthly_status(session, target)
