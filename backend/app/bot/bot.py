import asyncio
import io

import discord
import logfire
from discord.message import Message
from discord.utils import setup_logging

from bot.agent.deps import WatsonDeps
from bot.agent.watson import watson_agent
from bot.workflows.attachment_processor import Expenses, process_attachment
from config import settings
from services.conversation import conversation_service
from utils.timezone import now_nepal

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

    deps = WatsonDeps()
    result = await watson_agent.run(
        message_content, message_history=message_history, deps=deps
    )
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

    if isinstance(result.output.response, str) and result.output.response.strip():
        sent = await message.channel.send(result.output.response)
        await conversation_service.append_conversation(
            conversation_id,
            message_ids=[sent.id],
        )

    for attachment in deps.attachments:
        sent = await message.channel.send(
            file=discord.File(io.BytesIO(attachment.content), attachment.filename)
        )
        await conversation_service.append_conversation(
            conversation_id,
            message_ids=[sent.id],
        )


async def run() -> None:
    setup_logging()
    async with client:
        await client.start(settings.DISCORD_TOKEN)
