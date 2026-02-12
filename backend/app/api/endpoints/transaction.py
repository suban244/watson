from schema.transaction import (
    TransactionCreate,
    TransactionRead,
)
from fastapi import APIRouter, Depends, HTTPException
from db.models import Transaction
from db.session import get_session
import uuid
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/", response_model=TransactionRead)
async def create_transaction(
    transaction: TransactionCreate,
    session: AsyncSession = Depends(get_session),
):
    new_transaction = Transaction(
        **transaction.model_dump(),
    )

    session.add(new_transaction)
    await session.commit()
    await session.refresh(new_transaction)
    return new_transaction


@router.get("/list/", response_model=list[TransactionRead])
async def get_transaction_list(
    session: AsyncSession = Depends(get_session),
):
    get_all_transactions_query = select(Transaction)
    result = await session.execute(get_all_transactions_query)
    db_transactions = result.scalars().all()

    return db_transactions


@router.get("/{transaction_id}/", response_model=TransactionRead)
async def get_transaction(
    transaction_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    transaction = await session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction
