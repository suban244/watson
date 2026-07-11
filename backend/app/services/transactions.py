"""Shared transaction queries used by both the API endpoints and the bot agent."""

import uuid
from collections.abc import Sequence

from paradedb.sqlalchemy import search
from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Transaction
from schema.transaction import TransactionCreate

Conditions = Sequence[ColumnElement[bool]]


async def create_transaction(
    session: AsyncSession, data: TransactionCreate
) -> Transaction:
    transaction = Transaction(**data.model_dump())
    session.add(transaction)
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def list_transactions(
    session: AsyncSession,
    *,
    conditions: Conditions = (),
    offset: int = 0,
    limit: int = 100,
) -> Sequence[Transaction]:
    query = (
        select(Transaction)
        .where(*conditions)
        .order_by(Transaction.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(query)
    return result.scalars().all()


async def search_transactions(
    session: AsyncSession,
    search_query: str,
    *,
    conditions: Conditions = (),
    offset: int = 0,
    limit: int = 20,
) -> Sequence[Transaction]:
    query = (
        select(Transaction)
        # use table column (ColumnElement) instead of InstrumentedAttribute to satisfy typing
        .where(
            search.match_any(Transaction.__table__.c.title, *search_query.split()),
            *conditions,
        )
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(query)
    return result.scalars().all()


async def list_categories(session: AsyncSession) -> list[str]:
    query = (
        select(Transaction.category).distinct().where(Transaction.category.isnot(None))
    )
    result = await session.execute(query)
    return [row[0] for row in result.fetchall()]


async def get_transaction(
    session: AsyncSession, transaction_id: uuid.UUID
) -> Transaction | None:
    return await session.get(Transaction, transaction_id)


async def update_transaction(
    session: AsyncSession, transaction_id: uuid.UUID, updates: dict
) -> Transaction | None:
    transaction = await session.get(Transaction, transaction_id)
    if transaction is None:
        return None
    for key, value in updates.items():
        setattr(transaction, key, value)
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def delete_transaction(session: AsyncSession, transaction_id: uuid.UUID) -> bool:
    transaction = await session.get(Transaction, transaction_id)
    if transaction is None:
        return False
    await session.delete(transaction)
    await session.commit()
    return True

