from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Transaction(BaseModel):
    amount: float
    title: str
    description: str | None = None
    is_expense: bool = True
    date: datetime

    category: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(Transaction):
    pass


class TransactionRead(Transaction):
    id: UUID
    pass


class TransactionUpdate(BaseModel):
    amount: float | None = None
    title: str | None = None
    description: str | None = None
    is_expense: bool | None = None
    date: datetime | None = None

    category: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TransactionSearch(BaseModel):
    search_query: str
