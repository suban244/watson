from db.session import async_session_maker
from services import reminders as reminder_service
from services.messaging import messaging_service
from taskiq_app import broker
from utils.timezone import now_nepal


@broker.task
async def dispatch_due_reminders() -> int:
    async with async_session_maker() as session:
        due = await reminder_service.claim_due(session, now_nepal())

    for reminder in due:
        messaging_service.send_message(
            {
                "type": "reminder",
                "data": {
                    "id": str(reminder.id),
                    "message": reminder.message,
                    "due_at": reminder.due_at.isoformat(),
                    "recurrence": reminder.recurrence,
                },
            }
        )

    return len(due)
