from db.models import Transaction
from db.session import async_session_maker
from datetime import datetime, time, timedelta
from taskiq_app import broker
from sqlalchemy import select, func, desc
from services.messaging import messaging_service
from utils.timezone import NEPAL_TZ, now_nepal


@broker.task
async def calculate_expenses_of_last_week():
    today = now_nepal().date()
    last_sunday = today - timedelta(days=today.weekday() + 1)
    last_week_start = last_sunday - timedelta(days=6)

    # Full Monday-through-Sunday window: [start of Monday, start of next Monday)
    week_start = datetime.combine(last_week_start, time.min, tzinfo=NEPAL_TZ)
    week_end = datetime.combine(
        last_sunday + timedelta(days=1), time.min, tzinfo=NEPAL_TZ
    )
    last_week_conditions = (
        Transaction.date >= week_start,
        Transaction.date < week_end,
        Transaction.is_expense,
    )

    async with async_session_maker() as session:
        expense_per_category_query = (
            select(Transaction.category, func.sum(Transaction.amount))
            .where(*last_week_conditions)
            .group_by(Transaction.category)
        )
        result = (await session.execute(expense_per_category_query)).all()
        expense_per_category: dict[str, float] = {
            category: float(amount) for category, amount in result
        }

        major_expenses_query = (
            select(Transaction)
            .where(*last_week_conditions)
            .order_by(desc(Transaction.amount))
            .limit(5)
        )
        major_expenses = (await session.execute(major_expenses_query)).scalars().all()

    summary = {
        "period_start": last_week_start.isoformat(),
        "period_end": last_sunday.isoformat(),
        "total_expense": sum(expense_per_category.values()),
        "expense_per_category": expense_per_category,
        "major_expenses": [
            {
                "date": tx.date.astimezone(NEPAL_TZ).isoformat()
                if tx.date.tzinfo
                else tx.date.isoformat(),
                "category": tx.category,
                "amount": float(tx.amount),
                "description": tx.description,
            }
            for tx in major_expenses
        ],
    }

    message = {
        "type": "weekly_expense_summary",
        "data": summary,
    }

    messaging_service.send_message(message)

    return summary
