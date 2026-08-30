from pydantic import BaseModel
from datetime import date, timedelta
from fastapi import HTTPException, Query
from db.models import Transaction
from services.tags import slugify
from sqlalchemy.sql.elements import ColumnElement
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
        categories: list[str] = Query(
            None, description="Filter transactions by categories"
        ),
        tags: list[str] = Query(
            None,
            description="Filter to transactions carrying any of these tag slugs",
        ),
        date_from: date = Query(
            None, description="Filter transactions from this date (YYYY-MM-DD)"
        ),
        date_to: date = Query(
            None, description="Filter transactions up to this date (YYYY-MM-DD)"
        ),
        month: str = Query(
            None,
            description="Filter to a whole calendar month (YYYY-MM), NPT-anchored",
        ),
        is_expense: bool = Query(
            None, description="Filter transactions by expense type"
        ),
        amount_min: float = Query(
            None,
            description="Filter transactions with amount greater than or equal to this value",
        ),
        amount_max: float = Query(
            None,
            description="Filter transactions with amount less than or equal to this value",
        ),
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
