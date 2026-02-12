from services.attachment_processor import (
    attachment_processor,
    Classifier,
    State,
    Expenses,
)
import json
import asyncio
from redis.asyncio.client import Redis
import discord
from discord.utils import setup_logging
from discord.message import Message
from core.config import settings
import logfire

from agent.base_finance_agent import finance_agent, Context
from agent.financial_tasks import summary_agent

logfire.configure(
    token=settings.LOGFIRE_TOKEN,
    service_name="discord-bot",
    send_to_logfire="if-token-present",
    environment=settings.APP_ENV,
    scrubbing=False,
    distributed_tracing=True,
)
logfire.instrument_pydantic_ai()
logfire.instrument_httpx()


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

    logfire.info(
        "Received message", message=message, reference=message.reference, id=message.id
    )

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
            logfire.info(
                f"Parsed expenses: {result.output}", expense_items=result.output
            )
            message_content += f"\nParsed Expenses from attachment :\n{result.output}"

    response = await finance_agent.run(message_content, deps=context)
    if context.send_final_response:
        await message.channel.send(response.output)


async def start_discord_bot():
    setup_logging()
    async with client:
        await client.start(settings.DISCORD_TOKEN)


async def handle_message(message: str | None):
    if message is None:
        return
    logfire.info(f"Received message from Redis Pub/Sub: {message}")

    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        logfire.error("Received invalid JSON message.")
        return

    channel = client.get_channel(int(settings.SOURCE_CHANNEL_ID))
    if not channel:
        return
    if isinstance(data, str):
        await channel.send(data)  # type: ignore

    if isinstance(data, dict):
        match data.get("type"):
            case "weekly_expense_summary":
                summary = data.get("data", {})
                response = await summary_agent.run(
                    f"Provide a weekly expense summary based on the following data:\n{summary}"
                )
                await channel.send(response.output)  # type: ignore

    return


async def check_task_queue():
    async_redis = Redis.from_url(settings.CELERY_BROKER_URL)
    pubsub = async_redis.pubsub()
    await pubsub.subscribe("default")

    try:
        while True:
            try:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message:
                    await handle_message(message=message["data"])

            except Exception as e:
                logfire.error(f"Error processing Redis Pub/Sub message: {e}")
    finally:
        await pubsub.unsubscribe()
        await async_redis.close()


async def main():
    tasks = [
        start_discord_bot(),
        check_task_queue(),
    ]
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logfire.info("Shutting down...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
