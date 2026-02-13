from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.review import ClientReview, ExecutorComplaint
    from app.models.user import User


class OrderStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DELETED = "deleted"
    CLOSED_NO_RESPONSE = "closed_no_response"
    COMPLETED = "completed"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    client_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)

    category: Mapped[str] = mapped_column(String(50), index=True)
    description: Mapped[str] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(100), index=True)
    contact: Mapped[str] = mapped_column(String(100))  # Phone or @username

    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), default=OrderStatus.ACTIVE, index=True)
    city_locked: Mapped[bool] = mapped_column(Boolean, default=False)

    expires_in_minutes: Mapped[int] = mapped_column(Integer, default=60)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # When customer responds after executor contact
    customer_responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    client: Mapped["User"] = relationship("User", back_populates="orders_created", foreign_keys=[client_id])
    executor_takes: Mapped[list["ExecutorTake"]] = relationship(
        "ExecutorTake", back_populates="order", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["ClientReview"]] = relationship(back_populates="order")
    complaints: Mapped[list["ExecutorComplaint"]] = relationship(back_populates="order")


class ExecutorTake(Base):
    __tablename__ = "executor_takes"
    __table_args__ = (
        UniqueConstraint("order_id", "executor_id", name="uq_executor_take_per_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(32), ForeignKey("orders.id"), index=True)
    executor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="executor_takes")
    executor: Mapped["User"] = relationship("User")
