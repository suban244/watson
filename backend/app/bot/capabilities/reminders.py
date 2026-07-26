import uuid

from pydantic_ai.capabilities import Capability

from db.models import Reminder
from db.session import async_session_maker
from services import reminders as reminder_service
from utils.timezone import now_nepal, parse_datetime

RECURRENCES = ("daily", "weekly", "monthly", "yearly")


def format_reminder(reminder: Reminder) -> str:
    recurrence = f" ({reminder.recurrence})" if reminder.recurrence else ""
    return (
        f"- id={reminder.id} | {reminder.message} "
        f"| {reminder.due_at.isoformat()}{recurrence}"
    )


reminders = Capability(
    id="reminders",
    description="Set, list, and cancel reminders.",
    defer_loading=True,
    instructions="""\
Reminders domain:
- Never show raw reminder ids to the user; they are for tool calls only.
- Default hour for date-only reminders is 09:00 NPT — mention this default in
  your reply if the user didn't specify a time.

Reminder workflows:
1. Set a reminder:
    - Trigger: user asks to be reminded of something, with a date/time that's
      actually inferable ("on the 5th", "tomorrow at 6pm", "every month on the
      1st").
    - Steps:
        1. Parse message, date, optional time, optional recurrence
           (daily/weekly/monthly/yearly).
        2. Call `set_reminder`.
        3. You can only return success_marker as your response.
    - If the request is genuinely ambiguous ("soon", "sometime next week") or
      the given time has already passed today, ask ONE short clarifying
      question instead of guessing. Don't ask when a reasonable guess is
      possible (e.g. "the 5th" with no time -> next upcoming 5th at the
      default hour).

2. List reminders:
    - Trigger: user asks what reminders they have.
    - Steps:
        1. Call `list_reminders`.
        2. Return a human-readable bullet list (message, when, recurrence)
           as your response, never the raw ids.

3. Cancel a reminder:
    - Trigger: user wants to cancel/remove a reminder, referring to it by
      description ("the landlord one"), never by id.
    - Steps:
        1. Call `list_reminders` to find the matching reminder's id.
        2. Call `cancel_reminder` with that id.
        3. You can only return success_marker as your response.

4. Editing an existing reminder (e.g. "make this the 3rd of every month
   instead", replying to a fired reminder):
    - Steps:
        1. Identify the reminder id from conversation context or `list_reminders`.
        2. Call `cancel_reminder` on the old one, then `set_reminder` with the
           updated details.
        3. You can only return success_marker as your response.
""",
)


@reminders.tool_plain
async def set_reminder(
    message: str,
    date: str,
    time: str | None = None,
    recurrence: str | None = None,
) -> str:
    """Create a reminder.
    Args:
        message: What to remind the user about (e.g. "Pay rent").
        date: The date of the (first) reminder in YYYY-MM-DD format.
        time: The time in 24-hour HH:MM format. Omit to default to 09:00 NPT.
        recurrence: One of "daily", "weekly", "monthly", "yearly", or omit for
            a one-off reminder.
    """
    if recurrence is not None and recurrence not in RECURRENCES:
        return f"Invalid recurrence. Must be one of: {', '.join(RECURRENCES)}."

    due_at = parse_datetime(date, time)
    if due_at is None:
        return (
            "Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time."
        )

    if recurrence is None and due_at <= now_nepal():
        return (
            "That time has already passed. Ask the user to confirm the intended "
            "date/time (e.g. did they mean tomorrow?)."
        )

    async with async_session_maker() as session:
        reminder = await reminder_service.create_reminder(
            session, message, due_at, recurrence
        )
    return (
        f"Reminder set: {message} at {due_at.isoformat()}"
        f"{f' ({recurrence})' if recurrence else ''}. Reminder ID: {reminder.id}."
    )


@reminders.tool_plain
async def list_reminders() -> str:
    """List all pending reminders, ordered by when they're next due."""
    async with async_session_maker() as session:
        results = await reminder_service.list_pending(session)
    if not results:
        return "No pending reminders."

    response = "Pending reminders:\n"
    for reminder in results:
        response += format_reminder(reminder) + "\n"
    return response


@reminders.tool_plain
async def cancel_reminder(reminder_id: str) -> str:
    """Cancel a pending reminder.
    Args:
        reminder_id: The id of the reminder to cancel (from `list_reminders`).
    """
    try:
        parsed_id = uuid.UUID(reminder_id)
    except ValueError:
        return "Invalid reminder id."

    async with async_session_maker() as session:
        cancelled = await reminder_service.cancel_reminder(session, parsed_id)
    if not cancelled:
        return "Reminder not found or already cancelled/sent."
    return "Reminder cancelled."
