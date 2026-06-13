import uuid

import logfire
from sqlalchemy import cast, select, text
from sqlalchemy.dialects.postgresql import JSONB, insert as pg_insert
from sqlalchemy.sql import func
from paradedb.sqlalchemy import search

from bot.schema import DiscordTransaction
from db.models import DiscordConversation
from db.models import Transaction as TransactionModel
from db.session import async_session_maker
from schema.transaction import TransactionRead


class DBService:
    @logfire.instrument("add_transaction", record_return=True)
    async def add_transaction(self, transaction_data: DiscordTransaction) -> dict:
        async with async_session_maker() as session:
            new_transaction = TransactionModel(**transaction_data.model_dump())
            session.add(new_transaction)
            await session.commit()
            await session.refresh(new_transaction)
            return TransactionRead.model_validate(new_transaction).model_dump(mode="json")

    @logfire.instrument("search_transactions", record_return=True)
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
            return [TransactionRead.model_validate(t).model_dump(mode="json") for t in transactions]

    @logfire.instrument("get_transaction", record_return=True)
    async def get_transaction(self, transaction_id: uuid.UUID) -> dict | None:
        async with async_session_maker() as session:
            transaction = await session.get(TransactionModel, transaction_id)
            if transaction is None:
                return None
            return TransactionRead.model_validate(transaction).model_dump(mode="json")

    @logfire.instrument("update_transaction", record_return=True)
    async def update_transaction(self, transaction_id: uuid.UUID, update_data: dict) -> dict | None:
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

    @logfire.instrument("delete_transaction", record_return=True)
    async def delete_transaction(self, transaction_id: uuid.UUID) -> int:
        async with async_session_maker() as session:
            transaction = await session.get(TransactionModel, transaction_id)
            if transaction is None:
                return 404
            await session.delete(transaction)
            await session.commit()
            return 204

    @logfire.instrument("find_conversation_by_message", record_return=True)
    async def find_conversation_by_message(self, discord_message_id: int) -> dict | None:
        async with async_session_maker() as session:
            result = await session.execute(
                select(DiscordConversation).where(
                    DiscordConversation.message_ids.contains(cast([discord_message_id], JSONB))
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return {
                "conversation_id": row.conversation_id,
                "messages": row.messages,
                "message_ids": row.message_ids,
            }

    @logfire.instrument("get_conversation", record_return=True)
    async def get_conversation(self, conversation_id: int) -> dict:
        async with async_session_maker() as session:
            row = await session.get(DiscordConversation, conversation_id)
            if row is None:
                return {"conversation_id": conversation_id, "messages": [], "message_ids": []}
            return {
                "conversation_id": row.conversation_id,
                "messages": row.messages,
                "message_ids": row.message_ids,
            }

    @logfire.instrument("save_conversation", record_return=True)
    async def save_conversation(
        self, conversation_id: int, messages: list[dict], message_ids: list[int]
    ) -> None:
        async with async_session_maker() as session:
            stmt = (
                pg_insert(DiscordConversation)
                .values(
                    conversation_id=conversation_id,
                    messages=messages,
                    message_ids=message_ids,
                    updated_at=func.now(),
                )
                .on_conflict_do_update(
                    index_elements=["conversation_id"],
                    set_={
                        "messages": messages,
                        "message_ids": message_ids,
                        "updated_at": func.now(),
                    },
                )
            )
            await session.execute(stmt)
            await session.commit()

    @logfire.instrument("run_sql", record_return=True)
    async def run_sql(self, query: str) -> list[dict]:
        async with async_session_maker() as session:
            result = await session.execute(
                text(query), execution_options={"postgresql_readonly": True}
            )
            return [dict(row) for row in result.mappings().all()]


db_service = DBService()
