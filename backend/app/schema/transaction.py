from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class Transaction(BaseModel):
    amount: float
    title: str
    description: str
    is_income: bool
    date: datetime

    tags: list[UUID] = []

    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(Transaction):
    pass


class TransactionRead(Transaction):
    pass


class Tag(BaseModel):
    name: str
    description: str

    model_config = ConfigDict(from_attributes=True)


class TagCreate(Tag):
    pass


class TagRead(Tag):
    id: UUID
    pass


class TagLimit(BaseModel):
    tag: UUID
    limit: float


class BudgetConfig(BaseModel):
    tag_limits: list[TagLimit] = []


class Budget(BaseModel):
    name: str
    description: str
    start_date: datetime
    end_date: datetime

    budget_config: BudgetConfig

    model_config = ConfigDict(from_attributes=True)
