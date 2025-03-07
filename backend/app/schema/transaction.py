from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class Transaction(BaseModel):
    amount: float
    title: str
    description: str
    is_income: bool
    date: datetime

    sub_category: UUID

    model_config = ConfigDict(from_attributes=True)


class SubCategory(BaseModel):
    name: str
    description: str

    category: UUID

    model_config = ConfigDict(from_attributes=True)


class Category(BaseModel):
    name: str
    description: str

    model_config = ConfigDict(from_attributes=True)


class Budget(BaseModel):
    name: str
    description: str
    start_date: datetime
    end_date: datetime

    budget_config: dict

    model_config = ConfigDict(from_attributes=True)


class SubCategoryLimit(BaseModel):
    sub_category: UUID
    limit: float

    model_config = ConfigDict(from_attributes=True)


class BudgetConfig(BaseModel):
    sub_category_limits: list[SubCategoryLimit] = []
