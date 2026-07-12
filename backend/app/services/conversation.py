import logfire
from sqlalchemy import cast, select
from sqlalchemy.dialects.postgresql import JSONB, insert as pg_insert
from sqlalchemy.sql import func
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

from db.models import DiscordConversation
from db.session import async_session_maker


class ConversationService:
    @logfire.instrument(record_return=True)
    async def find_conversation_by_message(
        self, discord_message_id: int
    ) -> tuple[list[ModelMessage], int | None]:
        async with async_session_maker() as session:
            result = await session.execute(
                select(DiscordConversation).where(
                    DiscordConversation.message_ids.contains(
                        cast([discord_message_id], JSONB)
                    )
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                return [], None
            messages = ModelMessagesTypeAdapter.validate_python(row.messages)
            return messages, row.conversation_id

    @logfire.instrument(record_return=True)
    async def get_or_create_conversation(
        self, message_id: int, reference_message_id: int | None = None
    ) -> tuple[list[ModelMessage] | None, int]:
        if reference_message_id is not None:
            messages, conversation_id = await self.find_conversation_by_message(
                reference_message_id
            )
            if conversation_id is not None:
                return messages, conversation_id
        return None, message_id

    @logfire.instrument(record_return=True)
    async def get_conversation(
        self, conversation_id: int
    ) -> tuple[list[ModelMessage], list[int]]:
        async with async_session_maker() as session:
            row = await session.get(DiscordConversation, conversation_id)
            if row is None:
                return [], []
            messages = ModelMessagesTypeAdapter.validate_python(row.messages)
            return messages, row.message_ids

    @logfire.instrument("Appending to conversation", record_return=True)
    async def append_conversation(
        self,
        conversation_id: int,
        messages: list[ModelMessage] | None = None,
        message_ids: list[int] | None = None,
    ) -> None:
        messages_dicts = (
            ModelMessagesTypeAdapter.dump_python(messages, mode="json")
            if messages
            else []
        )
        ids = message_ids or []

        conflict_set: dict = {"updated_at": func.now()}
        if messages:
            conflict_set["messages"] = DiscordConversation.messages.op("||")(
                cast(messages_dicts, JSONB)
            )
        if message_ids:
            conflict_set["message_ids"] = DiscordConversation.message_ids.op("||")(
                cast(ids, JSONB)
            )

        async with async_session_maker() as session:
            stmt = (
                pg_insert(DiscordConversation)
                .values(
                    conversation_id=conversation_id,
                    messages=messages_dicts,
                    message_ids=ids,
                    updated_at=func.now(),
                )
                .on_conflict_do_update(
                    index_elements=["conversation_id"],
                    set_=conflict_set,
                )
            )
            await session.execute(stmt)
            await session.commit()


conversation_service = ConversationService()
