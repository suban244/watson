from pydantic import BaseModel


class DiscordConversationRead(BaseModel):
    conversation_id: int
    messages: list[dict]
    message_ids: list[int]

    model_config = {"from_attributes": True}


class DiscordConversationUpdate(BaseModel):
    messages: list[dict]
    message_ids: list[int]


class DiscordConversationAppend(BaseModel):
    messages: list[dict]
    message_ids: list[int]
