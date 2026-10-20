"""Manual triggers for background jobs, gated by the internal token rather than
left open like the dashboard's data endpoints."""

import asyncio
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.deps import verify_internal_token
from services import weekly_summaries
from tasks.external.prabin_spotify.send_invoices import (
    send_invoice,
    send_prabin_spotify_invoices,
)
from tasks.finances.send_weekly_summary import send_weekly_summary

router = APIRouter(dependencies=[Depends(verify_internal_token)])


class SingleInvoiceParams(BaseModel):
    email: str
    multiplier: float = 1.0
    name: str


@router.post("/send-spotify-invoices/")
async def trigger_spotify_invoices():
    await send_prabin_spotify_invoices.kiq()
    return {"status": "Invoice job enqueued"}


@router.post("/send-spotify-invoice/")
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


@router.post("/weekly-summary/")
async def trigger_weekly_summary(
    as_of: Annotated[
        date | None,
        Query(
            description="Review the Monday-Sunday week before this day; defaults to today"
        ),
    ] = None,
):
    task = await send_weekly_summary.kiq(as_of=as_of)
    return {"status": "Weekly summary job enqueued", "task_id": task.task_id}


@router.delete("/weekly-summaries/", status_code=204)
async def clear_weekly_summaries():
    """Forget past weekly reviews, so the next one starts without them."""
    await weekly_summaries.clear()
