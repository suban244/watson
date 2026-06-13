from db.models import DiscordConversation
from db.session import get_session
from fastapi import APIRouter, Depends
from schema.discord_message import (
    DiscordConversationAppend,
    DiscordConversationRead,
    DiscordConversationUpdate,
)
from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB, insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/by-message/{discord_message_id}/", response_model=DiscordConversationRead | None)
async def find_conversation_by_message(
    discord_message_id: int,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(DiscordConversation).where(
            DiscordConversation.message_ids.contains(
                cast([discord_message_id], JSONB)
            )
        )
    )
    return result.scalar_one_or_none()


@router.get("/{conversation_id}/", response_model=DiscordConversationRead)
async def get_conversation(
    conversation_id: int,
    session: AsyncSession = Depends(get_session),
):
    row = await session.get(DiscordConversation, conversation_id)
    if row is None:
        return DiscordConversationRead(conversation_id=conversation_id, messages=[], message_ids=[])
    return row


@router.post("/{conversation_id}/append/", status_code=204)
async def append_to_conversation(
    conversation_id: int,
    payload: DiscordConversationAppend,
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        pg_insert(DiscordConversation)
        .values(
            conversation_id=conversation_id,
            messages=payload.messages,
            message_ids=payload.message_ids,
            updated_at=func.now(),
        )
        .on_conflict_do_update(
            index_elements=["conversation_id"],
            set_={
                "messages": DiscordConversation.messages.op("||")(
                    cast(payload.messages, JSONB)
                ),
                "message_ids": DiscordConversation.message_ids.op("||")(
                    cast(payload.message_ids, JSONB)
                ),
                "updated_at": func.now(),
            },
        )
    )
    await session.execute(stmt)
    await session.commit()


@router.put("/{conversation_id}/", response_model=DiscordConversationRead)
async def upsert_conversation(
    conversation_id: int,
    payload: DiscordConversationUpdate,
    session: AsyncSession = Depends(get_session),
):
    row = await session.get(DiscordConversation, conversation_id)
    if row is None:
        row = DiscordConversation(
            conversation_id=conversation_id,
            messages=payload.messages,
            message_ids=payload.message_ids,
        )
        session.add(row)
    else:
        row.messages = payload.messages
        row.message_ids = payload.message_ids
    await session.commit()
    await session.refresh(row)
    return row
