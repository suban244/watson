import asyncio
import json

import discord
import logfire
from discord.message import Message
from discord.utils import setup_logging
from redis.asyncio.client import Redis

from bot.agent.base_finance_agent import Context, finance_agent
from bot.agent.financial_tasks import summary_agent
from bot.services.attachment_processor import Classifier, Expenses, State, attachment_processor
from bot.services.conversation import conversation_service
from config import settings

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_message(message: Message):
    if str(message.channel.id) != settings.SOURCE_CHANNEL_ID:
        return
    if message.author == client.user:
        return

    logfire.info("Received message", message=message, reference=message.reference, id=message.id)
    await message.add_reaction("👀")

    context = Context(message=message)

    attachment_results = await asyncio.gather(
        *[
            attachment_processor.run(
                start_node=Classifier(image_url=attachment.url), state=State()
            )
            for attachment in message.attachments
        ]
    )
    message_content = message.content
    for result in attachment_results:
        if isinstance(result.output, Expenses):
            logfire.info(f"Parsed expenses: {result.output}", expense_items=result.output)
            message_content += f"\nParsed Expenses from attachment:\n{result.output}"

    if message.reference and message.reference.message_id:
        message_history, conversation_id = await conversation_service.find_conversation_by_message(
            message.reference.message_id
        )
        if conversation_id is None:
            conversation_id = message.id
    else:
        message_history, conversation_id = await conversation_service.create_conversation(message.id)

    response = await finance_agent.run(
        message_content, deps=context, message_history=message_history
    )
    logfire.debug(
        "Agent response",
        response=response.output,
        new_messages=response.new_messages(),
        new_messages_json=response.new_messages_json(),
    )

    all_messages = list(message_history) + list(response.new_messages())
    await conversation_service.save_conversation(
        conversation_id,
        all_messages,
        [message.id],
    )

    if context.send_final_response:
        await message.channel.send(response.output)


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
            case _:
                logfire.warning(f"Unknown Redis message type: {parsed.get('type')!r}")
    else:
        logfire.warning(f"Unknown Redis message format: {type(parsed)}, value: {parsed!r}")


async def _check_task_queue() -> None:
    async_redis = Redis.from_url(settings.REDIS_URL)
    pubsub = async_redis.pubsub()
    await pubsub.subscribe("default")
    try:
        while True:
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and "data" in message:
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    await _handle_redis_message(data)
            except Exception as e:
                logfire.error(f"Error processing Redis Pub/Sub message: {e}")
    finally:
        await pubsub.unsubscribe()
        await async_redis.close()


async def run() -> None:
    setup_logging()
    async with client:
        await asyncio.gather(
            client.start(settings.DISCORD_TOKEN),
            _check_task_queue(),
        )
