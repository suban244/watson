import uuid

from db.models import Transaction
from db.session import get_session
from fastapi import APIRouter, Depends, HTTPException
from schema.transaction import (
    TransactionCreate,
    TransactionRead,
    TransactionSearch,
    TransactionUpdate,
)
from sqlalchemy import select, text
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


@router.post("/search/", response_model=list[TransactionRead])
async def search_transactions(
    search: TransactionSearch,
    session: AsyncSession = Depends(get_session),
):
    search_transactions_query = (
        select(Transaction)
        .order_by(text(
            "3 * (title <@> to_bm25query(:query, 'ix_transaction_title_bm25'))"
            " + COALESCE(description <@> to_bm25query(:query, 'ix_transaction_description_bm25'), 0)"
        ))
        .limit(10)
        .params(query=search.search_query)
    )

    result = await session.execute(search_transactions_query)
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


@router.patch("/{transaction_id}/", response_model=TransactionRead)
async def update_transaction(
    transaction_id: uuid.UUID,
    transaction_update: TransactionUpdate,
    session: AsyncSession = Depends(get_session),
):
    transaction = await session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    for key, value in transaction_update.model_dump().items():
        setattr(transaction, key, value)

    await session.commit()
    return transaction


@router.delete("/{transaction_id}/", status_code=204)
async def delete_transaction(
    transaction_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    transaction = await session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    await session.delete(transaction)
    await session.commit()
