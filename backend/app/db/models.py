import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Index,
    String,
    Text,
    column,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import DeclarativeBase, Mapped, declarative_mixin, mapped_column
from sqlalchemy.sql import func
from paradedb.sqlalchemy import indexing


class Base(DeclarativeBase):
    pass


@declarative_mixin
class PrimaryTimestamped(Base):
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now,
        onupdate=func.now(),
        nullable=False,
    )
    meta: Mapped[dict | None] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=True
    )


@declarative_mixin
class PrimaryUUIDTimestamped(PrimaryTimestamped):
    __abstract__ = True
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)


class Transaction(PrimaryUUIDTimestamped):
    __tablename__ = "transactions"

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_expense: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    category: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Category of the transaction"
    )

    __table_args__ = (
        Index("ix_transactions_date", "date"),
        Index("ix_transactions_is_expense", "is_expense"),
        Index("ix_transactions_category", "category"),
        Index(
            "ix_transactions_bm25",
            indexing.BM25Field(column("id")),
            indexing.BM25Field(column("title")),
            indexing.BM25Field(column("description")),
            postgresql_using="bm25",
            postgresql_with={"key_field": "id"},
        ),
    )


class ReminderStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    CANCELLED = "cancelled"


class Reminder(PrimaryUUIDTimestamped):
    __tablename__ = "reminders"

    message: Mapped[str] = mapped_column(Text, nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recurrence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReminderStatus.PENDING
    )

    __table_args__ = (Index("ix_reminders_status_due_at", "status", "due_at"),)


class DiscordConversation(PrimaryTimestamped):
    __tablename__ = "discord_conversations"

    conversation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    messages: Mapped[list] = mapped_column(
        MutableList.as_mutable(JSONB), nullable=False, default=list
    )
    message_ids: Mapped[list] = mapped_column(
        MutableList.as_mutable(JSONB), nullable=False, default=list
    )
    __table_args__ = (
        Index(
            "ix_discord_conversations_message_ids",
            "message_ids",
            postgresql_using="gin",
        ),
    )


# class Budget(PrimaryUUIDTimestamped):
#     __tablename__ = "budgets"

#     name: Mapped[str] = mapped_column(String(255), nullable=False)
#     description: Mapped[str] = mapped_column(Text, nullable=True)

#     start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
#     end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

#     budget_config: Mapped[dict] = mapped_column(
#         MutableDict.as_mutable(JSONB), nullable=True
#     )
