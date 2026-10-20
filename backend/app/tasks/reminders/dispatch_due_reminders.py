from datetime import datetime, timedelta

from pydantic_ai.messages import ModelResponse, TextPart

from db.session import async_session_maker
from services import reminders as reminder_service
from services.conversation import conversation_service
from services.discord_channel import watson_channel
from services.reminders import DueReminder
from taskiq_app import broker
from utils.timezone import now_nepal

OVERDUE_THRESHOLD = timedelta(minutes=2)


def _format_due(due_at: datetime) -> str:
    return due_at.strftime("%b %-d, %-I:%M %p")


def _reminder_text(reminder: DueReminder) -> str:
    if now_nepal() - reminder.due_at > OVERDUE_THRESHOLD:
        return (
            f"⏰ **Reminder** *(overdue — was due {_format_due(reminder.due_at)})*: "
            f"{reminder.message}"
        )
    return f"⏰ **Reminder:** {reminder.message}"


@broker.task
async def dispatch_due_reminders() -> int:
    async with async_session_maker() as session:
        due = await reminder_service.claim_due(session, now_nepal())

    if not due:
        return 0

    async with watson_channel() as channel:
        for reminder in due:
            sent = await channel.send(_reminder_text(reminder))

            synthetic_response = ModelResponse(
                parts=[
                    TextPart(
                        content=(
                            f'Reminder fired: "{reminder.message}" '
                            f"(due {reminder.due_at.isoformat()}, "
                            f"recurrence={reminder.recurrence or 'none'}, "
                            f"id={reminder.id}). "
                            "If the user replies about this, use the reminders "
                            "tools (cancel_reminder / set_reminder) to act on it."
                        )
                    )
                ]
            )
            await conversation_service.append_conversation(
                sent.id, [synthetic_response], [sent.id]
            )

    return len(due)
