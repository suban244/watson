from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from pydantic_ai import Agent
from typing import Literal
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from bot.capabilities import watson_capabilities
from config import settings


def instructions() -> str:
    date_today = datetime.now(ZoneInfo("Asia/Kathmandu")).date()
    return f"""\
You are Watson, a finance agent that helps users manage their expenses.
The currency is NPR (Nepalese Rupee).

Domain Keywords:
Pathao: (a ride-hailing service in Nepal)

Rules:
- When answering a question, return the answer text as your response.
- Never show raw transaction ids to the user; they are for tool calls only.
- If a step fails, return a text response explaining what went wrong.

Date Today: {date_today}

You will use
"""


class SuccessMarker(BaseModel):
    success: Literal[True] = True


class AgentResponse(BaseModel):
    response: str | SuccessMarker


def _make_model() -> OpenRouterModel:
    return OpenRouterModel(
        # model_name="moonshotai/kimi-k2.6",
        model_name="openai/gpt-5.6-luna",
        # model_name="openai/gpt-oss-120b",
        provider=OpenRouterProvider(api_key=settings.OPENROUTER_API_KEY),
    )


watson_agent = Agent(
    model=_make_model(),
    instructions=instructions,
    output_type=AgentResponse,
    capabilities=[watson_capabilities],
)
