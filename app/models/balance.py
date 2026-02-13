from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class TransactionType(str, Enum):
    RECHARGE = "recharge"
    ORDER_TAKE = "order_take"
    REFUND = "refund"


class BalanceTransaction(Base):
    __tablename__ = "balance_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)

    type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType), index=True)
    amount: Mapped[int] = mapped_column(Integer)  # rubles (negative for deductions)
    balance_after: Mapped[int] = mapped_column(Integer)

    order_id: Mapped[str | None] = mapped_column(String(32))  # if related to order
    payment_method: Mapped[str | None] = mapped_column(String(50))  # telegram_stars, card, etc
    external_transaction_id: Mapped[str | None] = mapped_column(String(255))

    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="balance_transactions")
