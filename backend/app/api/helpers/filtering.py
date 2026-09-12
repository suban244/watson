from datetime import date, timedelta
from typing import Annotated

from fastapi import HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.sql.elements import ColumnElement

from db.models import Transaction
from services.tags import slugify
from utils.timezone import day_start_npt, month_bounds, parse_month_key


class TransactionFilter(BaseModel):
    categories: list[str] | None = None
    tags: list[str] | None = None

    date_from: date | None = None
    date_to: date | None = None
    month: date | None = None

    is_expense: bool | None = None
    amount_min: float | None = None
    amount_max: float | None = None

    @classmethod
    def get_filterset(
        cls,
        *,
        categories: Annotated[
            list[str] | None,
            Query(description="Filter transactions by categories"),
        ] = None,
        tags: Annotated[
            list[str] | None,
            Query(description="Filter to transactions carrying any of these tag slugs"),
        ] = None,
        date_from: Annotated[
            date | None,
            Query(description="Filter transactions from this date (YYYY-MM-DD)"),
        ] = None,
        date_to: Annotated[
            date | None,
            Query(description="Filter transactions up to this date (YYYY-MM-DD)"),
        ] = None,
        month: Annotated[
            str | None,
            Query(
                description="Filter to a whole calendar month (YYYY-MM), NPT-anchored"
            ),
        ] = None,
        is_expense: Annotated[
            bool | None, Query(description="Filter transactions by expense type")
        ] = None,
        amount_min: Annotated[
            float | None,
            Query(
                description="Filter transactions with amount greater than or equal to this value"
            ),
        ] = None,
        amount_max: Annotated[
            float | None,
            Query(
                description="Filter transactions with amount less than or equal to this value"
            ),
        ] = None,
    ):
        try:
            parsed_month = parse_month_key(month) if month else None
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail="month must be YYYY-MM"
            ) from exc

        return cls(
            categories=categories,
            tags=tags,
            date_from=date_from,
            date_to=date_to,
            month=parsed_month,
            is_expense=is_expense,
            amount_min=amount_min,
            amount_max=amount_max,
        )

    def get_conditions(self) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = []
        if self.categories:
            conditions.append(Transaction.category.in_(self.categories))
        if self.tags:
            # `&&` (any overlap), served by the GIN index on transactions.tags.
            # Slugified so a display name in the query string still matches.
            conditions.append(
                Transaction.tags.overlap([slugify(tag) for tag in self.tags])
            )
        if self.date_from:
            conditions.append(Transaction.date >= day_start_npt(self.date_from))
        if self.date_to:
            conditions.append(
                Transaction.date < day_start_npt(self.date_to + timedelta(days=1))
            )
        if self.month:
            start, end = month_bounds(self.month)
            conditions += [Transaction.date >= start, Transaction.date < end]
        if self.is_expense is not None:
            conditions.append(Transaction.is_expense == self.is_expense)
        if self.amount_min is not None:
            conditions.append(Transaction.amount >= self.amount_min)
        if self.amount_max is not None:
            conditions.append(Transaction.amount <= self.amount_max)
        return conditions
