from fastapi import APIRouter, Depends, Header, HTTPException
from .endpoints.discord_message import router as discord_message_router
from .endpoints.transaction import router as transaction_router
from db.session import get_session
from sqlalchemy import text
from pydantic import BaseModel
from config import settings
from tasks.external.prabin_spotify.send_invoices import (
    send_prabin_spotify_invoices,
    _inject_globals,
    _send_one,
    _TEMPLATE,
)

from sqlalchemy.ext.asyncio import AsyncSession


class QueryParams(BaseModel):
    query: str


class SingleInvoiceParams(BaseModel):
    email: str
    multiplier: float = 1.0
    name: str


async def verify_internal_token(x_internal_token: str = Header(...)):
    if x_internal_token != settings.INTERNAL_API_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")


router = APIRouter()

router.get("/")(lambda: {"Hello": "Welcome To Watson Router"})

router.include_router(transaction_router, prefix="/transactions", tags=["transactions"])
router.include_router(
    discord_message_router, prefix="/discord-messages", tags=["discord-messages"]
)


@router.post(
    "/tasks/send-spotify-invoices/", dependencies=[Depends(verify_internal_token)]
)
async def trigger_spotify_invoices():
    await send_prabin_spotify_invoices.kiq()
    return {"status": "Invoice job enqueued"}


@router.post(
    "/tasks/send-spotify-invoice/", dependencies=[Depends(verify_internal_token)]
)
async def send_single_spotify_invoice(params: SingleInvoiceParams):
    base_html = _inject_globals(_TEMPLATE.read_text(encoding="utf-8"))
    ok = _send_one(params.email, base_html, params.multiplier, params.name)
    if not ok:
        raise HTTPException(
            status_code=500, detail=f"Failed to send invoice to {params.email}"
        )
    return {"status": "Invoice sent", "email": params.email}


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
