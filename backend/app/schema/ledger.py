from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from schema.person import PersonRead
from schema.transaction import TransactionCreate, TransactionRead
from schema.types import StrUUID

SIGN_CONVENTION = "positive means they owe you, negative means you owe them"


class LedgerEntryCreate(BaseModel):
    amount: float = Field(description=f"Signed: {SIGN_CONVENTION}.")
    title: str
    date: datetime
    transaction_id: UUID | None = None


class LedgerEntryRead(LedgerEntryCreate):
    id: StrUUID
    person_id: StrUUID
    transaction_id: StrUUID | None = None

    model_config = ConfigDict(from_attributes=True)


class LedgerShare(BaseModel):
    person_id: UUID
    amount: float = Field(description="What this person owes you, positive.")


class PersonBalance(PersonRead):
    balance: float = Field(description=f"Net across every entry: {SIGN_CONVENTION}.")
    entry_count: int


class PersonLedger(PersonRead):
    balance: float = Field(description=f"Net across every entry: {SIGN_CONVENTION}.")
    entries: list[LedgerEntryRead] = Field(
        description="Newest first, and only as many as were asked for."
    )


class LedgerEntryResult(BaseModel):
    entry: LedgerEntryRead
    person: PersonRead
    balance: float = Field(description=f"After this entry: {SIGN_CONVENTION}.")


class SharedExpenseCreate(BaseModel):
    expense: TransactionCreate = Field(
        description="Your share only, not the bill total."
    )
    shares: list[LedgerShare] = Field(min_length=1)


class SharedEntryRead(LedgerEntryRead):
    nickname: str


class SharedExpenseRead(BaseModel):
    transaction: TransactionRead
    entries: list[SharedEntryRead]
