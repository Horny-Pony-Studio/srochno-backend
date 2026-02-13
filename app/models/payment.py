from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.balance import BalanceTransaction
    from app.models.user import User


class InvoiceStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"


class PaymentInvoice(Base):
    __tablename__ = "payment_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)

    crypto_bot_invoice_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    amount: Mapped[int] = mapped_column(Integer)  # RUB
    status: Mapped[InvoiceStatus] = mapped_column(
        SQLEnum(InvoiceStatus), default=InvoiceStatus.PENDING, index=True
    )

    pay_url: Mapped[str | None] = mapped_column(String(512))
    mini_app_invoice_url: Mapped[str | None] = mapped_column(String(512))

    balance_transaction_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("balance_transactions.id")
    )

    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    balance_transaction: Mapped["BalanceTransaction"] = relationship("BalanceTransaction")
