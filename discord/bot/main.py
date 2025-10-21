import asyncio
from redis.asyncio.client import Redis
import discord
from discord.utils import setup_logging
from discord.message import Message
from core.config import settings
import logfire

from agent.base_finance_agent import finance_agent, Context

logfire.configure(
    token=settings.LOGFIRE_TOKEN,
    service_name="discord-bot",
    send_to_logfire="if-token-present",
)
logfire.instrument_pydantic_ai()


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

    context = Context(message=message)

    await message.add_reaction("👀")
    response = await finance_agent.run(message.content, deps=context)
    if context.send_final_response:
        await message.channel.send(response.output)


async def start_discord_bot():
    setup_logging()
    async with client:
        await client.start(settings.DISCORD_TOKEN)


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
                    logfire.info(
                        f"Received message from Redis Pub/Sub: {message['data']}"
                    )
                    channel = client.get_channel(int(settings.SOURCE_CHANNEL_ID))
                    if channel:
                        await channel.send(message["data"].decode())  # type: ignore
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
