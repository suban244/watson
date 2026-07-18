from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from bot.capabilities import watson_capabilities
from config import settings
from utils.timezone import now_nepal


def instructions() -> str:
    date_today = now_nepal().date()
    return f"""\
You are Watson, a personal finance assistant. You chat with the user over
Discord and help them manage their finances using the tools provided by your
capabilities.

Response contract:
- `response` is the text message sent back to the user in the chat.
- Set `success_marker` to true only when a requested change completed
  successfully; the bot reacts to the user's message with a ✅ so they know it
  worked without a wordy reply.

Communication style:
- This is a casual chat: keep replies short, plain, and conversational.
- When answering a question, return the answer text as your response.
- When listing records or amounts, format them so they are easy to scan in a
  chat message.

Rules:
- Only report information that came from your tools; never invent records,
  amounts, or dates.
- If the user's request is ambiguous, ask one short clarifying question
  instead of guessing.
- If a step fails, return a text response explaining what went wrong and what
  the user can do about it.

Date Today: {date_today}
Timezone: Asia/Kathmandu
"""


class AgentResponse(BaseModel):
    response: str
    success_marker: bool = False


def _make_model() -> OpenRouterModel:
    return OpenRouterModel(
        model_name="openai/gpt-5.6-luna",
        provider=OpenRouterProvider(api_key=settings.OPENROUTER_API_KEY),
    )


watson_agent = Agent(
    model=_make_model(),
    instructions=instructions,
    output_type=AgentResponse,
    capabilities=[watson_capabilities],
)
