from pydantic_ai import Agent

from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.providers.mistral import MistralProvider
from core.config import settings


model = MistralModel(
    "mistral-medium-2508", provider=MistralProvider(api_key=settings.MISTRAL_API_KEY)
)

SUMMARY_GENERATE_INSTRUCTIONS = """\
You are a financial summary agent that provides users with a concise summary of their expenses over a specified period.
Your summary should include the total amount spent, the number of transactions, and a breakdown of expenses by category.
Ensure that the summary is clear and easy to understand.
"""

summary_agent = Agent(model=model, instructions=SUMMARY_GENERATE_INSTRUCTIONS)

