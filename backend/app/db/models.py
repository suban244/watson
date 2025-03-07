import uuid
from datetime import datetime

from sqlalchemy import DateTime
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


# class Category(PrimaryUUIDTimestamped):
#     __tablename__ = "categories"

#     name: Mapped[str] = mapped_column(String(255), nullable=False)
#     description: Mapped[str] = mapped_column(Text, nullable=True)

#     sub_catagories: Mapped[list["SubCategory"]] = relationship("SubCategory", back_populates="category")

# class SubCategory(PrimaryUUIDTimestamped):
#     __tablename__ = "sub_categories"

#     name: Mapped[str] = mapped_column(String(255), nullable=False)
#     description: Mapped[str] = mapped_column(Text, nullable=True)

#     transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="sub_category")

#     category: Mapped[Category] = relationship("Category", back_populates="sub_categories")
#     category_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("categories.id"), nullable=False)


# class Transaction(PrimaryUUIDTimestamped):
#     __tablename__ = "transactions"

#     amount: Mapped[float] = mapped_column(Float, nullable=False)
#     title: Mapped[str] = mapped_column(String(255), nullable=False)
#     description: Mapped[str] = mapped_column(Text, nullable=True)
#     is_income: Mapped[bool] = mapped_column(Boolean, nullable=False)
#     date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

#     sub_category: Mapped[SubCategory] = relationship("SubCategory", back_populates="transactions")
#     sub_category_id: Mapped[uuid.UUID]= mapped_column(UUID, ForeignKey("sub_categories.id"), nullable=True)


# class Budget(PrimaryUUIDTimestamped):
#     __tablename__ = "budgets"

#     name: Mapped[str] = mapped_column(String(255), nullable=False)
#     description: Mapped[str] = mapped_column(Text, nullable=True)

#     start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
#     end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

#     budget_config: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSONB), nullable=True)
