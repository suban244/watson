from schema.transaction import (
    TransactionCreate,
    SubCategoryCreate,
    CategoryCreate,
    TransactionRead,
    SubCategoryRead,
    CategoryRead,
)
from fastapi import APIRouter, Depends, HTTPException
from db.models import Transaction, SubCategory, Category
from db.session import get_session
import uuid
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/transaction", response_model=TransactionRead)
async def create_transaction(
    transaction: TransactionCreate, session: AsyncSession = Depends(get_session)
):
    new_transaction = Transaction(**transaction.model_dump())
    session.add(new_transaction)
    await session.commit()
    return new_transaction


@router.post("/sub_category", response_model=SubCategoryRead)
async def create_sub_category(
    sub_category: SubCategoryCreate, session: AsyncSession = Depends(get_session)
):
    new_sub_category = SubCategory(**sub_category.model_dump())
    session.add(new_sub_category)
    await session.commit()
    return new_sub_category


@router.post("/category", response_model=CategoryRead)
async def create_category(
    category: CategoryCreate, session: AsyncSession = Depends(get_session)
):
    new_category = Category(**category.model_dump())
    session.add(new_category)
    await session.commit()
    return new_category


@router.get("/category/list", response_model=list[CategoryRead])
async def get_category_list(session: AsyncSession = Depends(get_session)):
    categories = await session.execute(select(Category))
    return categories


@router.get("/transaction/{transaction_id}", response_model=TransactionRead)
async def get_transaction(
    transaction_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    transaction = await session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction
