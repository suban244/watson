from db.session import get_session
from fastapi import APIRouter, Depends
from schema.tag import BudgetOverview
from services import budget as budget_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/overview/", response_model=BudgetOverview)
async def get_overview(session: AsyncSession = Depends(get_session)):
    """Active pots with their spend to date, plus this calendar month's totals."""
    return await budget_service.overview(session)
