import discord
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


client.run(settings.DISCORD_TOKEN)
