import io
from datetime import date, timedelta

import discord

from bot.agent.deps import WatsonDeps
from bot.agent.weekly_summary import weekly_summary_agent, weekly_summary_prompt
from db.session import async_session_maker
from services import weekly_summaries
from services.budget import ensure_monthly_budget
from services.conversation import conversation_service
from services.discord_channel import watson_channel
from services.weekly_summaries import PastReview
from taskiq_app import broker
from utils.timezone import today_nepal


@broker.task
async def send_weekly_summary(as_of: date | None = None) -> str:
    """Review the week (Monday to Sunday) before `as_of` and post it to Discord.

    `as_of` defaults to today; pass an earlier date to rerun or test the review
    of a past week, e.g. `await send_weekly_summary.kiq(as_of=date(2026, 9, 15))`.
    """
    today = as_of or today_nepal()
    last_sunday = today - timedelta(days=today.weekday() + 1)
    last_monday = last_sunday - timedelta(days=6)

    # Most months have no budget row until something asks for one, and the agent
    # reads `monthly_budgets` directly with SQL, which would find nothing.
    async with async_session_maker() as session:
        await ensure_monthly_budget(session, last_sunday)

    previous = await weekly_summaries.recent()
    deps = WatsonDeps()
    result = await weekly_summary_agent.run(
        weekly_summary_prompt(last_monday, last_sunday, previous), deps=deps
    )

    files = [
        discord.File(io.BytesIO(attachment.content), attachment.filename)
        for attachment in deps.attachments
    ]
    async with watson_channel() as channel:
        sent = await channel.send(result.output, files=files)

    # Keyed on the posted message, so replying to it continues with the queries
    # and numbers behind the review in context.
    await conversation_service.append_conversation(
        sent.id, list(result.new_messages()), [sent.id]
    )
    await weekly_summaries.remember(
        PastReview(period_start=last_monday, text=result.output)
    )
    return result.output
