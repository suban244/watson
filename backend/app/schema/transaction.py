from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class Transaction(BaseModel):
    amount: float
    title: str
    description: str
    is_income: bool
    date: datetime

    sub_category_id: UUID | None

    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(BaseModel):
    pass


class TransactionRead(BaseModel):
    pass


class SubCategory(BaseModel):
    name: str
    description: str

    category_id: UUID | None

    model_config = ConfigDict(from_attributes=True)


class SubCategoryCreate(BaseModel):
    pass


class SubCategoryRead(BaseModel):
    pass


class Category(BaseModel):
    name: str
    description: str
    # maybe add colors ?

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(BaseModel):
    pass


class CategoryRead(BaseModel):
    pass


class SubCategoryLimit(BaseModel):
    sub_category: UUID
    limit: float

    model_config = ConfigDict(from_attributes=True)


class BudgetConfig(BaseModel):
    sub_category_limits: list[SubCategoryLimit] = []


class Budget(BaseModel):
    name: str
    description: str
    start_date: datetime
    end_date: datetime

    budget_config: BudgetConfig

    model_config = ConfigDict(from_attributes=True)
