from schema.transaction import (
    TransactionCreate,
    TransactionRead,
)
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from db.models import Transaction, Tag
from db.session import get_session
import uuid
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from .tags import get_all_tags

router = APIRouter()


@router.post("/", response_model=TransactionRead)
async def create_transaction(
    transaction: TransactionCreate,
    session: AsyncSession = Depends(get_session),
    tags: list[Tag] = Depends(get_all_tags),
):
    tag_id_to_tag_name_map = {str(tag.id): tag.name for tag in tags}
    new_transaction = Transaction(
        **transaction.model_dump(exclude={"tags"}),
        tags=jsonable_encoder(transaction.tags),
    )

    # ensure all tags are valid
    for tag in transaction.tags:
        if tag not in tag_id_to_tag_name_map:
            raise HTTPException(status_code=400, detail=f"Tag {tag} does not exist")

    session.add(new_transaction)
    await session.commit()
    return new_transaction


@router.get("/list/", response_model=list[TransactionRead])
async def get_transaction_list(
    session: AsyncSession = Depends(get_session),
    tags: list[Tag] = Depends(get_all_tags),
):
    get_all_transactions_query = select(Transaction)
    result = await session.execute(get_all_transactions_query)
    db_transactions = result.scalars().all()

    transactions: list[TransactionRead] = []
    tag_id_to_tag_name_map = {str(tag.id): tag.name for tag in tags}
    for transaction in db_transactions:
        transaction_tags = []
        for tag in transaction.tags:
            if tag in tag_id_to_tag_name_map:
                transaction_tags.append(tag_id_to_tag_name_map[tag])

        transactions.append(
            TransactionRead(
                amount=transaction.amount,
                title=transaction.title,
                description=transaction.description,
                is_income=transaction.is_income,
                date=transaction.date,
                tags=transaction_tags,
            )
        )

    return transactions


@router.get("/{transaction_id}/", response_model=TransactionRead)
async def get_transaction(
    transaction_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    transaction = await session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction
