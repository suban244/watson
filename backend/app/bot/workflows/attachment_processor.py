import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent, ImageUrl
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.providers.mistral import MistralProvider

from config import settings


class SingleExpense(BaseModel):
    title: str = Field(...)
    description: str | None
    amount: int = Field(
        ..., description="Amount in NPR. Round it to the ceiling if in decimal."
    )
    transaction_date: str | None = Field(
        ..., description="Transaction date in yyyy-mm-dd format, if available"
    )


class Expenses(BaseModel):
    expenses: list[SingleExpense]


class FinancialDocument(BaseModel):
    pass


class CannotClassify(BaseModel):
    pass


model = MistralModel(
    "mistral-medium-2508", provider=MistralProvider(api_key=settings.MISTRAL_API_KEY)
)

expense_extractor_agent = Agent(
    model=model,
    output_type=Expenses,
    instructions="""\
You are a financial receipt parser. You will be given a bill and your job is to parse
the contents of the bill and create a list of itemized items.
""",
)

document_classifier = Agent(
    model=model,
    output_type=FinancialDocument | CannotClassify,
    system_prompt=(
        'Classify the document in the image url as "FinancialDocument" '
        "if it is a financial document like a receipt, invoice, bill etc."
    ),
)


@logfire.instrument(record_return=True)
async def process_attachment(image_url: str) -> Expenses | CannotClassify:
    """Extract itemized expenses from an image if it is a financial document."""
    classification = await document_classifier.run(
        user_prompt=[ImageUrl(url=image_url)]
    )
    if not isinstance(classification.output, FinancialDocument):
        return CannotClassify()

    extraction = await expense_extractor_agent.run(
        user_prompt=[ImageUrl(url=image_url)]
    )
    return extraction.output
