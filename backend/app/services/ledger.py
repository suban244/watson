import uuid
from collections.abc import Sequence
from datetime import datetime

import logfire
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import LedgerEntry, Person, Transaction
from schema.ledger import LedgerEntryCreate, LedgerShare, PersonBalance
from schema.person import PersonRead
from schema.transaction import TransactionCreate
from services import tags as tag_service


async def add_entry(
    session: AsyncSession, person_id: uuid.UUID, data: LedgerEntryCreate
) -> LedgerEntry:
    entry = LedgerEntry(person_id=person_id, **data.model_dump())
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def get_entry(session: AsyncSession, entry_id: uuid.UUID) -> LedgerEntry | None:
    return await session.get(LedgerEntry, entry_id)


async def list_entries(
    session: AsyncSession,
    *,
    person_id: uuid.UUID | None = None,
    limit: int = 50,
) -> Sequence[LedgerEntry]:
    query = (
        select(LedgerEntry)
        .order_by(LedgerEntry.date.desc(), LedgerEntry.created_at.desc())
        .limit(limit)
    )
    if person_id is not None:
        query = query.where(LedgerEntry.person_id == person_id)

    result = await session.execute(query)
    return result.scalars().all()


async def person_balance(session: AsyncSession, person_id: uuid.UUID) -> float:
    query = select(func.coalesce(func.sum(LedgerEntry.amount), 0.0)).where(
        LedgerEntry.person_id == person_id
    )
    return float((await session.execute(query)).scalar_one())


async def balances(session: AsyncSession) -> list[PersonBalance]:
    query = (
        select(
            Person,
            func.coalesce(func.sum(LedgerEntry.amount), 0.0).label("balance"),
            func.count(LedgerEntry.id).label("entry_count"),
        )
        .select_from(Person)
        .outerjoin(LedgerEntry, LedgerEntry.person_id == Person.id)
        .group_by(Person.id)
        .order_by(Person.nickname)
    )

    result = await session.execute(query)
    return [
        PersonBalance(
            **PersonRead.model_validate(person).model_dump(),
            balance=float(balance),
            entry_count=count,
        )
        for person, balance, count in result.all()
    ]


async def settle(
    session: AsyncSession,
    person_id: uuid.UUID,
    amount: float,
    *,
    title: str,
    date: datetime,
) -> LedgerEntry:
    """Record a repayment; the sign comes from the current balance, and
    overpayment is not clamped."""
    balance = await person_balance(session, person_id)
    if balance == 0:
        raise ValueError("Nothing is owed either way, so there is nothing to settle.")

    magnitude = abs(amount)
    signed = -magnitude if balance > 0 else magnitude

    return await add_entry(
        session,
        person_id,
        LedgerEntryCreate(amount=signed, title=title, date=date),
    )


@logfire.instrument(record_return=True)
async def record_shared_expense(
    session: AsyncSession,
    expense: TransactionCreate,
    shares: Sequence[LedgerShare],
) -> tuple[Transaction, list[LedgerEntry]]:
    """Your share as a transaction, everyone else's as linked entries — in one
    commit, so there is never an expense with nobody owing for it."""
    if not shares:
        raise ValueError("A shared expense needs at least one person to split with.")

    payload = expense.model_dump()
    payload["tags"] = await tag_service.resolve_slugs(session, payload["tags"])

    transaction = Transaction(**payload)
    session.add(transaction)
    await session.flush()

    entries = [
        LedgerEntry(
            person_id=share.person_id,
            amount=share.amount,
            title=expense.title,
            date=expense.date,
            transaction_id=transaction.id,
        )
        for share in shares
    ]
    session.add_all(entries)

    await session.commit()

    await session.refresh(transaction)
    for entry in entries:
        await session.refresh(entry)
    return transaction, entries


async def delete_entry(session: AsyncSession, entry_id: uuid.UUID) -> bool:
    entry = await session.get(LedgerEntry, entry_id)
    if entry is None:
        return False
    await session.delete(entry)
    await session.commit()
    return True
