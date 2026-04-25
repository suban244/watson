from db.models import Transaction
from db.session import sync_session_manager
from datetime import datetime, timedelta
from taskiq_app import broker
from sqlalchemy import select, func, desc
from services.messaging import messaging_service
from zoneinfo import ZoneInfo


@broker.task
def calculate_expenses_of_last_week():
    nepal_tz = ZoneInfo("Asia/Kathmandu")
    current_date = datetime.now(nepal_tz)

    last_sunday = current_date - timedelta(days=current_date.weekday() + 1)
    last_week_start = last_sunday - timedelta(days=6)

    with sync_session_manager() as session:
        total_expense_query = select(func.sum(Transaction.amount)).where(
            Transaction.date >= last_week_start,
            Transaction.date <= last_sunday,
            Transaction.is_expense,
        )
        total_expense = session.scalar(total_expense_query) or 0.0

        expense_per_category_query = (
            select(Transaction.category, func.sum(Transaction.amount))
            .where(
                Transaction.date >= last_week_start,
                Transaction.date <= last_sunday,
                Transaction.is_expense,
            )
            .group_by(Transaction.category)
        )
        result = session.execute(expense_per_category_query).all()
        expense_per_category: dict[str, float] = {
            category: float(amount) for category, amount in result
        }

        major_expenses_query = (
            select(Transaction)
            .where(
                Transaction.date >= last_week_start,
                Transaction.date <= last_sunday,
                Transaction.is_expense,
            )
            .order_by(desc(Transaction.amount))
            .limit(5)
        )
        major_expenses = session.execute(major_expenses_query).scalars().all()

    summary = {
        "period_start": last_week_start.astimezone(nepal_tz).isoformat(),
        "period_end": last_sunday.astimezone(nepal_tz).isoformat(),
        "total_expense": float(total_expense),
        "expense_per_category": expense_per_category,
        "major_expenses": [
            {
                "date": tx.date.astimezone(nepal_tz).isoformat()
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
