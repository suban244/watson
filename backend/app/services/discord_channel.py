"""Post to Watson's channel from processes that don't run the bot.

The bot's gateway connection lives in the API process; the taskiq worker posts
over Discord's REST API instead, which needs only the token. A session per call
is fine at this volume: a weekly summary and the odd due reminder.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import discord

from config import settings


@asynccontextmanager
async def watson_channel() -> AsyncGenerator[discord.abc.Messageable]:
    client = discord.Client(intents=discord.Intents.none())
    try:
        await client.login(settings.DISCORD_TOKEN)
        channel = await client.fetch_channel(int(settings.SOURCE_CHANNEL_ID))
        if not isinstance(channel, discord.abc.Messageable):
            raise TypeError(f"Channel {channel.id} can't be posted to")
        yield channel
    finally:
        await client.close()
