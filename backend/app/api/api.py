import asyncio

from fastapi import APIRouter, Depends, Header, HTTPException
from .endpoints.budget import router as budget_router
from .endpoints.tag import router as tag_router
from .endpoints.transaction import router as transaction_router
from pydantic import BaseModel
from config import settings
from tasks.external.prabin_spotify.send_invoices import (
    send_invoice,
    send_prabin_spotify_invoices,
)


class SingleInvoiceParams(BaseModel):
    email: str
    multiplier: float = 1.0
    name: str


async def verify_internal_token(x_internal_token: str = Header(...)):
    if x_internal_token != settings.INTERNAL_API_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")


router = APIRouter()


@router.get("/")
def router_root():
    return {"Hello": "Welcome To Watson Router"}


router.include_router(transaction_router, prefix="/transactions", tags=["transactions"])
router.include_router(tag_router, prefix="/tags", tags=["tags"])
router.include_router(budget_router, prefix="/budget", tags=["budget"])


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
    # SMTP is blocking; keep it off the event loop shared with the Discord bot.
    ok = await asyncio.to_thread(
        send_invoice, params.email, params.multiplier, params.name
    )
    if not ok:
        raise HTTPException(
            status_code=500, detail=f"Failed to send invoice to {params.email}"
        )
    return {"status": "Invoice sent", "email": params.email}
