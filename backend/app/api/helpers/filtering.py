from pydantic import BaseModel
from datetime import date
from fastapi import Query
from db.models import Transaction
from sqlalchemy.sql.elements import ColumnElement

class TransactionFilter(BaseModel):
    categories: list[str] | None = None
    date_from: date | None = None
    date_to: date | None = None
    is_expense: bool | None = None

    @classmethod
    def get_filterset(
        cls,
        categories: list[str] = Query(
            None, description="Filter transactions by categories"
        ),
        date_from: date  = Query(
            None, description="Filter transactions from this date (YYYY-MM-DD)"
        ),
        date_to: date = Query(
            None, description="Filter transactions up to this date (YYYY-MM-DD)"
        ),
        is_expense: bool = Query(
            None, description="Filter transactions by expense type"
        ),
    ):
        return cls(
            categories=categories,
            date_from=date_from,
            date_to=date_to,
            is_expense=is_expense,
        )

    def get_conditions(self) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = []
        if self.categories:
            conditions.append(Transaction.category.in_(self.categories))
        if self.date_from:
            conditions.append(Transaction.date >= self.date_from)
        if self.date_to:
            conditions.append(Transaction.date <= self.date_to)
        if self.is_expense is not None:
            conditions.append(Transaction.is_expense == self.is_expense)
        return conditions
