"""Shared reminder queries used by the bot agent and the dispatch task."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Reminder, ReminderStatus


class DueReminder(BaseModel):
    """A reminder as it was when it fired — captured before `claim_due`
    advances or closes the underlying row, so callers can report the time
    the user was actually promised rather than the next occurrence."""

    id: uuid.UUID
    message: str
    recurrence: str | None
    due_at: datetime


_RECURRENCE_STEPS = {
    "daily": relativedelta(days=1),
    "weekly": relativedelta(weeks=1),
    "monthly": relativedelta(months=1),
    "yearly": relativedelta(years=1),
}


async def create_reminder(
    session: AsyncSession,
    message: str,
    due_at: datetime,
    recurrence: str | None = None,
) -> Reminder:
    reminder = Reminder(message=message, due_at=due_at, recurrence=recurrence)
    session.add(reminder)
    await session.commit()
    await session.refresh(reminder)
    return reminder


async def list_pending(session: AsyncSession) -> Sequence[Reminder]:
    query = (
        select(Reminder)
        .where(Reminder.status == ReminderStatus.PENDING)
        .order_by(Reminder.due_at)
    )
    result = await session.execute(query)
    return result.scalars().all()


async def cancel_reminder(session: AsyncSession, reminder_id: uuid.UUID) -> bool:
    reminder = await session.get(Reminder, reminder_id)
    if reminder is None or reminder.status != ReminderStatus.PENDING:
        return False
    reminder.status = ReminderStatus.CANCELLED
    await session.commit()
    return True


async def claim_due(session: AsyncSession, now: datetime) -> Sequence[DueReminder]:
    """Select due, pending reminders and advance/close them in the same transaction.

    Idempotent if a sweep ever overlaps: rows are moved out of `pending`
    before the caller does anything with them.
    """
    query = (
        select(Reminder)
        .where(Reminder.status == ReminderStatus.PENDING, Reminder.due_at <= now)
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(query)
    due_rows = list(result.scalars().all())

    fired = [
        DueReminder(
            id=reminder.id,
            message=reminder.message,
            recurrence=reminder.recurrence,
            due_at=reminder.due_at,
        )
        for reminder in due_rows
    ]

    for reminder in due_rows:
        step = _RECURRENCE_STEPS.get(reminder.recurrence or "")
        if step is not None:
            next_due = reminder.due_at + step
            while next_due <= now:
                next_due += step
            reminder.due_at = next_due
        else:
            reminder.status = ReminderStatus.SENT

    await session.commit()
    return fired
