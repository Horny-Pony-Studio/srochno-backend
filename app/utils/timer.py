import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.services.balance_service import BalanceService

logger = logging.getLogger(__name__)


async def auto_close_expired_orders(db: AsyncSession) -> int:
    """
    Background task: Close orders that expired or got no customer response.
    Returns count of closed orders.
    """
    now = datetime.now(timezone.utc)
    closed_count = 0

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.executor_takes))
        .where(Order.status == OrderStatus.ACTIVE)
    )
    orders = result.scalars().all()

    for order in orders:
        expiry = order.created_at + timedelta(minutes=order.expires_in_minutes)

        if now >= expiry:
            order.status = OrderStatus.EXPIRED
            closed_count += 1

            # Update client counter
            client_result = await db.execute(
                select(User).where(User.id == order.client_id)
            )
            client = client_result.scalar_one_or_none()
            if client:
                client.active_orders_count = max(0, client.active_orders_count - 1)

            # Update executor counters
            for take in order.executor_takes:
                executor_result = await db.execute(
                    select(User).where(User.id == take.executor_id)
                )
                executor = executor_result.scalar_one_or_none()
                if executor:
                    executor.active_orders_count = max(0, executor.active_orders_count - 1)

        elif order.executor_takes and not order.customer_responded_at:
            first_take_time = min(take.taken_at for take in order.executor_takes)
            no_response_deadline = first_take_time + timedelta(
                minutes=settings.no_response_close_minutes
            )

            if now >= no_response_deadline:
                order.status = OrderStatus.CLOSED_NO_RESPONSE
                closed_count += 1

                # Update client counter
                client_result = await db.execute(
                    select(User).where(User.id == order.client_id)
                )
                client = client_result.scalar_one_or_none()
                if client:
                    client.active_orders_count = max(0, client.active_orders_count - 1)

                # Refund executors who paid and update counters
                for take in order.executor_takes:
                    executor_result = await db.execute(
                        select(User).where(User.id == take.executor_id)
                    )
                    executor = executor_result.scalar_one_or_none()
                    if executor:
                        executor.active_orders_count = max(0, executor.active_orders_count - 1)
                        await BalanceService.refund_order(
                            db, executor, order.id, settings.order_take_cost
                        )
                        logger.info(
                            "Refunded %d₽ to user %d for order %s",
                            settings.order_take_cost,
                            executor.id,
                            order.id,
                        )

    if closed_count > 0:
        await db.commit()
        logger.info("Auto-closed %d expired orders", closed_count)

    return closed_count
