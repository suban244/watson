import asyncio
import json
from datetime import datetime, timedelta

import discord
import logfire
from discord.message import Message
from discord.utils import setup_logging
from pydantic_ai.messages import ModelResponse, TextPart
from redis.asyncio.client import Redis

from bot.agent.watson import watson_agent
from bot.agent.financial_tasks import summary_agent
from bot.workflows.attachment_processor import Expenses, process_attachment
from services.conversation import conversation_service
from config import settings
from utils.timezone import now_nepal

# A reminder more than this far past its due_at is treated as having missed
# the normal 1-minute sweep (e.g. the worker was down) rather than just being
# a few seconds late.
OVERDUE_THRESHOLD = timedelta(minutes=2)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
@logfire.instrument(msg_template="Message: {message.content}", record_return=True)
async def on_message(message: Message):
    if str(message.channel.id) != settings.SOURCE_CHANNEL_ID:
        return
    if message.author == client.user:
        return

    await message.add_reaction("👀")

    attachment_results = await asyncio.gather(
        *[process_attachment(attachment.url) for attachment in message.attachments]
    )
    message_content = message.content
    for result in attachment_results:
        if isinstance(result, Expenses):
            logfire.info(f"Parsed expenses: {result}", expense_items=result)
            message_content += f"\nParsed Expenses from attachment:\n{result}"

    current_time = now_nepal()
    message_content += f"\n\nCurrent time (Nepal): {current_time.isoformat()}"

    reference_id = message.reference.message_id if message.reference else None
    (
        message_history,
        conversation_id,
    ) = await conversation_service.get_or_create_conversation(message.id, reference_id)

    result = await watson_agent.run(message_content, message_history=message_history)
    logfire.debug(
        "Agent response",
        response=result.output,
        new_messages=result.new_messages(),
        new_messages_json=result.new_messages_json(),
    )

    await conversation_service.append_conversation(
        conversation_id,
        list(result.new_messages()),
        [message.id],
    )

    if result.output.success_marker:
        await message.add_reaction("✅")

    if isinstance(result.output.response, str):
        if result.output.response.strip():
            sent = await message.channel.send(result.output.response)
            await conversation_service.append_conversation(
                conversation_id,
                message_ids=[sent.id],
            )


def _format_due(due_at: datetime) -> str:
    return due_at.strftime("%b %-d, %-I:%M %p")


async def _deliver_reminder(channel, data: dict) -> None:
    message = data.get("message", "")
    due_at_str = data.get("due_at")
    due_at = datetime.fromisoformat(due_at_str) if due_at_str else None
    recurrence = data.get("recurrence")
    reminder_id = data.get("id")

    if due_at is not None and now_nepal() - due_at > OVERDUE_THRESHOLD:
        text = f"⏰ **Reminder** *(overdue — was due {_format_due(due_at)})*: {message}"
    else:
        text = f"⏰ **Reminder:** {message}"

    sent = await channel.send(text)

    synthetic_response = ModelResponse(
        parts=[
            TextPart(
                content=(
                    f'Reminder fired: "{message}" (due {due_at_str}, '
                    f"recurrence={recurrence or 'none'}, id={reminder_id}). "
                    "If the user replies about this, use the reminders tools "
                    "(cancel_reminder / set_reminder) to act on it."
                )
            )
        ]
    )
    await conversation_service.append_conversation(
        sent.id,
        [synthetic_response],
        [sent.id],
    )


async def _handle_redis_message(data: str) -> None:
    logfire.info(f"Received message from Redis Pub/Sub: {data}")
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError:
        logfire.error("Received invalid JSON message.")
        return

    channel = client.get_channel(int(settings.SOURCE_CHANNEL_ID))
    if not channel:
        return

    if isinstance(parsed, str):
        await channel.send(parsed)  # type: ignore
    elif isinstance(parsed, dict):
        match parsed.get("type"):
            case "weekly_expense_summary":
                summary = parsed.get("data", {})
                result = await summary_agent.run(
                    f"Provide a weekly expense summary based on the following data:\n{summary}"
                )
                await channel.send(result.output)  # type: ignore
            case "reminder":
                await _deliver_reminder(channel, parsed.get("data", {}))
            case _:
                logfire.warning(f"Unknown Redis message type: {parsed.get('type')!r}")
    else:
        logfire.warning(
            f"Unknown Redis message format: {type(parsed)}, value: {parsed!r}"
        )


async def _check_task_queue() -> None:
    async_redis = Redis.from_url(settings.REDIS_URL)
    pubsub = async_redis.pubsub()
    await pubsub.subscribe("default")
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            try:
                await _handle_redis_message(data)
            except Exception as e:
                logfire.error(f"Error processing Redis Pub/Sub message: {e}")
    finally:
        await pubsub.unsubscribe()
        await async_redis.aclose()


async def run() -> None:
    setup_logging()
    async with client:
        await asyncio.gather(
            client.start(settings.DISCORD_TOKEN),
            _check_task_queue(),
        )
