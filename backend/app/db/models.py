import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import DeclarativeBase, Mapped, declarative_mixin, mapped_column
from sqlalchemy.sql import func


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
            "ix_transaction_title_bm25",
            "title",
            postgresql_using="bm25",
            postgresql_with={"text_config": "english"},
        ),
        Index(
            "ix_transaction_description_bm25",
            "description",
            postgresql_using="bm25",
            postgresql_with={"text_config": "english"},
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
