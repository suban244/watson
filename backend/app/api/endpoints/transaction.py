import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.deps import SessionDep
from api.helpers.filtering import TransactionFilter
from api.helpers.pagination import Pagination, PaginationPageSize
from schema.transaction import (
    CategoryOptions,
    ExpenseCategory,
    IncomeCategory,
    TransactionCreate,
    TransactionRead,
    TransactionSearch,
    TransactionUpdate,
)
from services import transactions as transaction_service

router = APIRouter()

PaginationDep = Annotated[PaginationPageSize, Depends(Pagination().page_size)]
FiltersDep = Annotated[TransactionFilter, Depends(TransactionFilter.get_filterset)]


@router.post("/", response_model=TransactionRead)
async def create_transaction(
    transaction: TransactionCreate,
    session: SessionDep,
):
    try:
        return await transaction_service.create_transaction(session, transaction)
    except ValueError as exc:
        # Unknown/archived tag slugs, or too many of them.
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/list/", response_model=list[TransactionRead])
async def get_transaction_list(
    session: SessionDep,
    pagination: PaginationDep,
    filters: FiltersDep,
):
    return await transaction_service.list_transactions(
        session,
        conditions=filters.get_conditions(),
        offset=(pagination.page - 1) * pagination.size,
        limit=pagination.size,
    )


@router.post("/search/", response_model=list[TransactionRead])
async def search_transactions(
    transaction_search: TransactionSearch,
    session: SessionDep,
    pagination: PaginationDep,
    filters: FiltersDep,
):
    return await transaction_service.search_transactions(
        session,
        transaction_search.search_query,
        conditions=filters.get_conditions(),
        offset=(pagination.page - 1) * pagination.size,
        limit=pagination.size,
    )


@router.get("/categories/", response_model=list[str])
async def get_categories(session: SessionDep):
    return await transaction_service.list_categories(session)


@router.get("/categories/options/", response_model=CategoryOptions)
async def get_category_options():
    return CategoryOptions(
        expense=[c.value for c in ExpenseCategory],
        income=[c.value for c in IncomeCategory],
    )


@router.get("/{transaction_id}/", response_model=TransactionRead)
async def get_transaction(transaction_id: uuid.UUID, session: SessionDep):
    transaction = await transaction_service.get_transaction(session, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.patch("/{transaction_id}/", response_model=TransactionRead)
async def update_transaction(
    transaction_id: uuid.UUID,
    transaction_update: TransactionUpdate,
    session: SessionDep,
):
    try:
        transaction = await transaction_service.update_transaction(
            session, transaction_id, transaction_update.model_dump(exclude_none=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.delete("/{transaction_id}/", status_code=204)
async def delete_transaction(
    transaction_id: uuid.UUID,
    session: SessionDep,
):
    deleted = await transaction_service.delete_transaction(session, transaction_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")
