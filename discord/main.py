import discord
from dotenv import load_dotenv
import os
from discord.message import Message
from discord.threads import Thread
from datetime import datetime

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_message(message: Message):
    channel_id = os.getenv("SOURCE_CHANNEL_ID", "")
    if str(message.channel.id) != channel_id:
        return

    if message.author == client.user:
        return

    d = datetime.now()
    d.strftime("%Y-%m-%d %H:%M:%S")

    thread: Thread = await message.create_thread(
        name=f"Thread-{d}",
        auto_archive_duration=60,
    )
    await thread.send("This is a thread message")

    if message.content.startswith("$hello"):
        await message.channel.send("Hello!")


client.run(os.getenv("DISCORD_TOKEN", ""))
