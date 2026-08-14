import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    Index,
    String,
    Text,
    column,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
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
    tags: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=list,
        server_default="{}",
        comment="Tag slugs; validated against tags.slug before write",
    )

    __table_args__ = (
        Index("ix_transactions_date", "date"),
        Index("ix_transactions_is_expense", "is_expense"),
        Index("ix_transactions_category", "category"),
        Index("ix_transactions_tags", "tags", postgresql_using="gin"),
        Index(
            "ix_transactions_bm25",
            indexing.BM25Field(column("id")),
            indexing.BM25Field(column("title")),
            indexing.BM25Field(column("description")),
            postgresql_using="bm25",
            postgresql_with={"key_field": "id"},
        ),
    )


class TagStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Tag(PrimaryUUIDTimestamped):
    """A label applied to transactions. A "pot" is a tag with `is_pot` set,
    optionally carrying a spending limit."""

    __tablename__ = "tags"

    slug: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        comment="Immutable identifier stored in transactions.tags",
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="When to apply this tag; rendered into the agent's instructions",
    )

    is_pot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TagStatus.ACTIVE
    )

    # Both only meaningful when `is_pot`; enforced in the service layer.
    exclude_from_monthly: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    limit_amount: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Null means the pot tracks spend with no limit"
    )

    __table_args__ = (Index("ix_tags_status", "status"),)


class MonthlyBudget(PrimaryTimestamped):
    """An override of the standard budget, for one month. Most months have no
    row and follow `DEFAULT_MONTHLY_LIMITS` in `schema.budget`."""

    __tablename__ = "monthly_budgets"

    month: Mapped[date] = mapped_column(
        Date, primary_key=True, comment="Always the 1st of the month, NPT"
    )
    limits: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Per-category limits keyed by ExpenseCategory value",
    )
    # Its own column, not a reserved key inside `limits` that could collide
    # with a category name.
    overall_limit: Mapped[float | None] = mapped_column(Float, nullable=True)


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
