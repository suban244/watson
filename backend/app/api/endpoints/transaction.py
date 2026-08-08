import uuid

from db.session import get_session
from fastapi import APIRouter, Depends, HTTPException
from schema.transaction import (
    CategoryOptions,
    ExpenseCategory,
    IncomeCategory,
    TransactionCreate,
    TransactionRead,
    TransactionSearch,
    TransactionUpdate,
)
from api.helpers.pagination import Pagination, PaginationPageSize
from api.helpers.filtering import TransactionFilter
from services import transactions as transaction_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/", response_model=TransactionRead)
async def create_transaction(
    transaction: TransactionCreate,
    session: AsyncSession = Depends(get_session),
):
    try:
        return await transaction_service.create_transaction(session, transaction)
    except ValueError as exc:
        # Unknown/archived tag slugs, or too many of them.
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/list/", response_model=list[TransactionRead])
async def get_transaction_list(
    session: AsyncSession = Depends(get_session),
    pagination: PaginationPageSize = Depends(Pagination().page_size),
    filters: TransactionFilter = Depends(TransactionFilter.get_filterset),
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
    session: AsyncSession = Depends(get_session),
    pagination: PaginationPageSize = Depends(Pagination().page_size),
    filters: TransactionFilter = Depends(TransactionFilter.get_filterset),
):
    return await transaction_service.search_transactions(
        session,
        transaction_search.search_query,
        conditions=filters.get_conditions(),
        offset=(pagination.page - 1) * pagination.size,
        limit=pagination.size,
    )


@router.get("/categories/", response_model=list[str])
async def get_categories(session: AsyncSession = Depends(get_session)):
    return await transaction_service.list_categories(session)


@router.get("/categories/options/", response_model=CategoryOptions)
async def get_category_options():
    return CategoryOptions(
        expense=[c.value for c in ExpenseCategory],
        income=[c.value for c in IncomeCategory],
    )


@router.get("/{transaction_id}/", response_model=TransactionRead)
async def get_transaction(
    transaction_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    transaction = await transaction_service.get_transaction(session, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.patch("/{transaction_id}/", response_model=TransactionRead)
async def update_transaction(
    transaction_id: uuid.UUID,
    transaction_update: TransactionUpdate,
    session: AsyncSession = Depends(get_session),
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
    session: AsyncSession = Depends(get_session),
):
    deleted = await transaction_service.delete_transaction(session, transaction_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")
