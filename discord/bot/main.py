import discord
from discord.message import Message
from agent.mistral_agent import MistralAgent
from agent.tools.add_expense import add_expense
from core.config import settings
import logfire

logfire.configure(
    token=settings.LOGFIRE_TOKEN,
    service_name="discord-bot",
    send_to_logfire="if-token-present",
)

mistral_agent = MistralAgent(api_key=settings.MISTRAL_API_KEY, tools=[add_expense])

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
    response = await mistral_agent.process_input(message.content)
    await message.channel.send(response)


client.run(settings.DISCORD_TOKEN)
