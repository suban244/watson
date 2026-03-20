from fastapi import APIRouter, Depends, Header, HTTPException
from .endpoints.transaction import router as transaction_router
from db.session import get_session
from sqlalchemy import text
from pydantic import BaseModel
from config import settings

from sqlalchemy.ext.asyncio import AsyncSession


class QueryParams(BaseModel):
    query: str


async def verify_internal_token(x_internal_token: str = Header(...)):
    if x_internal_token != settings.INTERNAL_API_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")


router = APIRouter()

router.get("/")(lambda: {"Hello": "Welcome To Watson Router"})

router.include_router(transaction_router, prefix="/transactions", tags=["transactions"])


@router.post("/sql/", dependencies=[Depends(verify_internal_token)])
async def run_sql(query: QueryParams, session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(
            text(query.query), execution_options={"postgresql_readonly": True}
        )
        data = result.mappings().all()
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
