import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import DeclarativeBase, Mapped, declarative_mixin, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import Boolean, Float, String, Text


class Base(DeclarativeBase):
    pass


@declarative_mixin
class PrimaryTimestamped(Base):
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=func.now(), nullable=False
    )
    meta: Mapped[dict | None] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=True
    )


@declarative_mixin
class PrimaryUUIDTimestamped(PrimaryTimestamped):
    __abstract__ = True
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)


class Tag(PrimaryUUIDTimestamped):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)


class Transaction(PrimaryUUIDTimestamped):
    __tablename__ = "transactions"

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_income: Mapped[bool] = mapped_column(Boolean, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    tags: Mapped[list[UUID]] = mapped_column(
        MutableList.as_mutable(JSONB), nullable=True
    )


class Budget(PrimaryUUIDTimestamped):
    __tablename__ = "budgets"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    budget_config: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=True
    )
