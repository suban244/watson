from schema.transaction import (
    TransactionCreate,
    TransactionRead,
    TagCreate,
    TagRead,
)
from fastapi import APIRouter, Depends, HTTPException
from db.models import Transaction, Tag
from db.session import get_session
import uuid
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/", response_model=TransactionRead)
async def create_transaction(
    transaction: TransactionCreate, session: AsyncSession = Depends(get_session)
):
    new_transaction = Transaction(**transaction.model_dump())
    session.add(new_transaction)
    await session.commit()
    return new_transaction


@router.post("/tag", response_model=TagRead)
async def create_tag(tag: TagCreate, session: AsyncSession = Depends(get_session)):
    new_tag = Tag(**tag.model_dump())
    session.add(new_tag)
    await session.commit()
    return new_tag


@router.get("/tag/list", response_model=list[TagRead])
async def get_tag_list(session: AsyncSession = Depends(get_session)):
    get_all_tags_query = select(Tag)
    result = await session.execute(get_all_tags_query)
    tags = result.scalars().all()
    return tags


@router.get("/{transaction_id}", response_model=TransactionRead)
async def get_transaction(
    transaction_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    transaction = await session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.get("/list", response_model=list[TransactionRead])
async def get_transaction_list(session: AsyncSession = Depends(get_session)):
    get_all_transactions_query = select(Transaction)
    result = await session.execute(get_all_transactions_query)
    transactions = result.scalars().all()
    return transactions
