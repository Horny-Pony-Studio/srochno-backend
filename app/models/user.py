from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, Enum):
    CLIENT = "client"
    EXECUTOR = "executor"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram user ID
    username: Mapped[str | None] = mapped_column(String(32), index=True)
    first_name: Mapped[str] = mapped_column(String(64))
    last_name: Mapped[str | None] = mapped_column(String(64))
    language_code: Mapped[str | None] = mapped_column(String(10))

    # Executor-specific
    balance: Mapped[int] = mapped_column(Integer, default=0)  # in rubles
    completed_orders_count: Mapped[int] = mapped_column(Integer, default=0)
    active_orders_count: Mapped[int] = mapped_column(Integer, default=0)
    average_rating: Mapped[float] = mapped_column(default=0.0)

    # Notification preferences
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    subscribed_categories: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    subscribed_cities: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    notification_frequency_minutes: Mapped[int] = mapped_column(Integer, default=10)
    last_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    orders_created: Mapped[list["Order"]] = relationship(
        "Order", back_populates="client", foreign_keys="Order.client_id"
    )
    balance_transactions: Mapped[list["BalanceTransaction"]] = relationship(back_populates="user")
    client_reviews: Mapped[list["ClientReview"]] = relationship(back_populates="client", foreign_keys="ClientReview.client_id")
    executor_complaints: Mapped[list["ExecutorComplaint"]] = relationship(back_populates="executor", foreign_keys="ExecutorComplaint.executor_id")
