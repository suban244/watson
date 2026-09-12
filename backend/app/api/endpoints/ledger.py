import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from schema.ledger import (
    LedgerEntryCreate,
    LedgerEntryRead,
    PersonBalance,
    SharedEntryRead,
    SharedExpenseCreate,
    SharedExpenseRead,
)
from services import ledger as ledger_service
from services import people as people_service

router = APIRouter()


@router.get("/balances/", response_model=list[PersonBalance])
async def get_balances(session: AsyncSession = Depends(get_session)):
    return await ledger_service.balances(session)


@router.get("/entries/", response_model=list[LedgerEntryRead])
async def get_entries(
    limit: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    return await ledger_service.list_entries(session, limit=limit)


@router.get("/people/{person_id}/entries/", response_model=list[LedgerEntryRead])
async def get_person_entries(
    person_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    if await people_service.get_person(session, person_id) is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return await ledger_service.list_entries(session, person_id=person_id, limit=limit)


@router.post("/people/{person_id}/entries/", response_model=LedgerEntryRead)
async def create_person_entry(
    person_id: uuid.UUID,
    entry: LedgerEntryCreate,
    session: AsyncSession = Depends(get_session),
):
    if await people_service.get_person(session, person_id) is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return await ledger_service.add_entry(session, person_id, entry)


@router.post("/shared-expense/", response_model=SharedExpenseRead)
async def create_shared_expense(
    payload: SharedExpenseCreate,
    session: AsyncSession = Depends(get_session),
):
    nicknames: dict[uuid.UUID, str] = {}
    for share in payload.shares:
        person = await people_service.get_person(session, share.person_id)
        if person is None:
            raise HTTPException(
                status_code=404, detail=f"No person with id {share.person_id}"
            )
        nicknames[person.id] = person.nickname

    try:
        transaction, entries = await ledger_service.record_shared_expense(
            session, payload.expense, payload.shares
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "transaction": transaction,
        "entries": [
            SharedEntryRead(
                **LedgerEntryRead.model_validate(entry).model_dump(),
                nickname=nicknames[entry.person_id],
            )
            for entry in entries
        ],
    }


@router.delete("/entries/{entry_id}/", status_code=204)
async def delete_entry(
    entry_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    if not await ledger_service.delete_entry(session, entry_id):
        raise HTTPException(status_code=404, detail="Ledger entry not found")
