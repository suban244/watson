import discord
from discord.message import Message
from core.config import settings
import logfire
from agent.schema.base import (
    ComponentEvent,
    MessageEvent,
    SuccessComponent,
    FailureComponent,
)
from agent.base_finance_agent import base_finance_agent

logfire.configure(
    token=settings.LOGFIRE_TOKEN,
    service_name="discord-bot",
    send_to_logfire="if-token-present",
)


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

    await message.add_reaction("👀")
    response = base_finance_agent.process_input(message.content)
    async for event in response:
        match event:
            case MessageEvent(content=content):
                await message.channel.send(content)
            case ComponentEvent(component=component):
                if isinstance(component, SuccessComponent):
                    await message.add_reaction("✅")
                elif isinstance(component, FailureComponent):
                    await message.add_reaction("❌")
                else:
                    logfire.error(f"Unknown component type: {component}")
            case _:
                logfire.error(f"Unknown event type: {event}")


client.run(settings.DISCORD_TOKEN)
