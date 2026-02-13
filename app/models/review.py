from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User


class ComplaintReason(str, Enum):
    NO_RESPONSE = "Не отвечал"
    CANCELLED_ORDER = "Отменил заказ"
    INADEQUATE_BEHAVIOR = "Неадекватное поведение"
    FALSE_INFO = "Ложная информация"
    OTHER = "Другое"


class ClientReview(Base):
    __tablename__ = "client_reviews"
    __table_args__ = (
        UniqueConstraint("order_id", "client_id", "executor_id", name="uq_client_review_per_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(32), ForeignKey("orders.id"), index=True)
    client_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    executor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)

    rating: Mapped[int] = mapped_column(Integer)  # 1-5
    comment: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="reviews")
    client: Mapped["User"] = relationship("User", back_populates="client_reviews", foreign_keys=[client_id])
    executor: Mapped["User"] = relationship("User", foreign_keys=[executor_id])


class ExecutorComplaint(Base):
    __tablename__ = "executor_complaints"
    __table_args__ = (
        UniqueConstraint("order_id", "executor_id", name="uq_executor_complaint_per_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(32), ForeignKey("orders.id"), index=True)
    executor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    client_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)

    complaint: Mapped[ComplaintReason] = mapped_column(SQLEnum(ComplaintReason))
    comment: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="complaints")
    executor: Mapped["User"] = relationship("User", back_populates="executor_complaints", foreign_keys=[executor_id])
    client: Mapped["User"] = relationship("User", foreign_keys=[client_id])
