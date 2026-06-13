from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ImageUrl
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from config import settings


class SingleExpense(BaseModel):
    title: str = Field(...)
    description: str | None
    amount: int = Field(..., description="Amount in NPR. Round it to the ceiling if in decimal.")
    transaction_date: str | None = Field(..., description="Transaction date in yyyy-mm-dd format, if available")


class Expenses(BaseModel):
    expenses: list[SingleExpense]


model = MistralModel(
    "mistral-medium-2508", provider=MistralProvider(api_key=settings.MISTRAL_API_KEY)
)

expense_extractor_agent = Agent[None, Expenses](
    model=model,
    output_type=Expenses,
    instructions="""\
You are a financial receipt parser. You will be given a bill and your job is to parse
the contents of the bill and create a list of itemized items.
""",
)


@dataclass
class State:
    pass


@dataclass
class ExpenseProcessor(BaseNode[State, None, Expenses]):
    image_url: str

    async def run(self, ctx: GraphRunContext[State]) -> End[Expenses]:
        res = await expense_extractor_agent.run(user_prompt=[ImageUrl(url=self.image_url)])
        return End(data=res.output)


class FinancialDocument(BaseModel):
    pass


class CannotClassify(BaseModel):
    pass


document_classifier = Agent[None, FinancialDocument | CannotClassify](
    model=model,
    output_type=FinancialDocument | CannotClassify,  # type: ignore
    system_prompt=(
        'Classify the document in the image url as "FinancialDocument" '
        "if it is a financial document like a receipt, invoice, bill etc."
    ),
)


@dataclass
class Classifier(BaseNode[State, None, Expenses | CannotClassify]):
    image_url: str

    async def run(self, ctx: GraphRunContext[State]) -> ExpenseProcessor | End[CannotClassify]:
        res = await document_classifier.run(user_prompt=[ImageUrl(url=self.image_url)])
        if isinstance(res.output, FinancialDocument):
            return ExpenseProcessor(image_url=self.image_url)
        else:
            return End(data=CannotClassify())


attachment_processor = Graph(nodes=[Classifier, ExpenseProcessor])
