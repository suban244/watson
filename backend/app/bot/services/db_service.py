import uuid

import logfire
from sqlalchemy import select, text
from paradedb.sqlalchemy import search

from bot.schema import DiscordTransaction
from db.models import Transaction as TransactionModel
from db.session import async_session_maker
from schema.transaction import TransactionRead


class DBService:
    @logfire.instrument(record_return=True)
    async def add_transaction(self, transaction_data: DiscordTransaction) -> dict:
        async with async_session_maker() as session:
            new_transaction = TransactionModel(**transaction_data.model_dump())
            session.add(new_transaction)
            await session.commit()
            await session.refresh(new_transaction)
            return TransactionRead.model_validate(new_transaction).model_dump(
                mode="json"
            )

    @logfire.instrument(record_return=True)
    async def search_transactions(self, search_query: str) -> list[dict]:
        async with async_session_maker() as session:
            query = (
                select(TransactionModel)
                .where(
                    search.match_any(
                        TransactionModel.__table__.c.title,
                        *search_query.split(),
                    )
                )
                .limit(20)
            )
            result = await session.execute(query)
            transactions = result.scalars().all()
            return [
                TransactionRead.model_validate(t).model_dump(mode="json")
                for t in transactions
            ]

    @logfire.instrument(record_return=True)
    async def get_transaction(self, transaction_id: uuid.UUID) -> dict | None:
        async with async_session_maker() as session:
            transaction = await session.get(TransactionModel, transaction_id)
            if transaction is None:
                return None
            return TransactionRead.model_validate(transaction).model_dump(mode="json")

    @logfire.instrument(record_return=True)
    async def update_transaction(
        self, transaction_id: uuid.UUID, update_data: dict
    ) -> dict | None:
        async with async_session_maker() as session:
            transaction = await session.get(TransactionModel, transaction_id)
            if transaction is None:
                return None
            for key, value in update_data.items():
                if value is not None:
                    setattr(transaction, key, value)
            await session.commit()
            await session.refresh(transaction)
            return TransactionRead.model_validate(transaction).model_dump(mode="json")

    @logfire.instrument(record_return=True)
    async def delete_transaction(self, transaction_id: uuid.UUID) -> int:
        async with async_session_maker() as session:
            transaction = await session.get(TransactionModel, transaction_id)
            if transaction is None:
                return 404
            await session.delete(transaction)
            await session.commit()
            return 204

    @logfire.instrument("run_sql", record_return=True)
    async def run_sql(self, query: str) -> list[dict]:
        async with async_session_maker() as session:
            result = await session.execute(
                text(query), execution_options={"postgresql_readonly": True}
            )
            return [dict(row) for row in result.mappings().all()]


db_service = DBService()
