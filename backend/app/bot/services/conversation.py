from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

from bot.services.db_service import db_service


class ConversationService:
    async def find_conversation_by_message(
        self, discord_message_id: int
    ) -> tuple[list[ModelMessage], int | None]:
        data = await db_service.find_conversation_by_message(discord_message_id)
        if data is None:
            return [], None
        messages = ModelMessagesTypeAdapter.validate_python(data["messages"])
        return messages, data["conversation_id"]

    async def create_conversation(
        self, message_id: int
    ) -> tuple[list[ModelMessage], int]:
        return [], message_id

    async def save_conversation(
        self,
        conversation_id: int,
        messages: list[ModelMessage],
        message_ids: list[int],
    ) -> None:
        messages_dicts = ModelMessagesTypeAdapter.dump_python(messages, mode="json")
        await db_service.save_conversation(conversation_id, messages_dicts, message_ids)


conversation_service = ConversationService()
