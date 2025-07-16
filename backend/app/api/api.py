from fastapi import APIRouter
from .endpoints.transaction import router as transaction_router
from fastapi import Depends
from db.session import get_session
from sqlalchemy import text
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession


class QueryParams(BaseModel):
    query: str


router = APIRouter()

router.get("/")(lambda: {"Hello": "Welcome To Watson Router"})

router.include_router(transaction_router, prefix="/transactions", tags=["transactions"])


@router.post("/sql/")
async def run_sql(query: QueryParams, session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(
            text(query.query), execution_options={"postgresql_readonly": True}
        )
        data = result.mappings().all()
        return data
    except Exception as e:
        return {"error": str(e)}
