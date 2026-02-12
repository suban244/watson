from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime


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
    id: uuid.UUID
