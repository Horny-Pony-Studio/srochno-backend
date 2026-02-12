import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.balance import BalanceTransaction, TransactionType
from app.models.order import ExecutorTake, Order, OrderStatus
from app.models.user import User
from app.schemas.order import CreateOrderRequest, UpdateOrderRequest

# Statuses visible in public listing
LISTABLE_STATUSES = {OrderStatus.ACTIVE, OrderStatus.EXPIRED, OrderStatus.COMPLETED}


class OrderService:
    @staticmethod
    def generate_order_id() -> str:
        return secrets.token_urlsafe(12)[:12]

    @staticmethod
    def is_expired(order: Order, now: datetime | None = None) -> bool:
        if now is None:
            now = datetime.now(timezone.utc)
        expiry = order.created_at + timedelta(minutes=order.expires_in_minutes)
        return now >= expiry

    @staticmethod
    def minutes_left(order: Order, now: datetime | None = None) -> int:
        if now is None:
            now = datetime.now(timezone.utc)
        expiry = order.created_at + timedelta(minutes=order.expires_in_minutes)
        remaining = (expiry - now).total_seconds() / 60
        return max(0, int(remaining))

    @staticmethod
    async def create_order(
        db: AsyncSession, user: User, request: CreateOrderRequest
    ) -> Order:
        result = await db.execute(
            select(Order).where(
                Order.contact == request.contact,
                Order.status == OrderStatus.ACTIVE,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This contact already has an active order",
            )

        order = Order(
            id=OrderService.generate_order_id(),
            client_id=user.id,
            category=request.category,
            description=request.description,
            city=request.city,
            contact=request.contact,
            city_locked=True,
            expires_in_minutes=settings.order_lifetime_minutes,
        )

        db.add(order)

        # Update counter
        user.active_orders_count += 1

        await db.commit()
        await db.refresh(order, ["executor_takes"])
        return order

    @staticmethod
    async def update_order(
        db: AsyncSession, order_id: str, user: User, request: UpdateOrderRequest
    ) -> Order:
        result = await db.execute(
            select(Order)
            .options(selectinload(Order.executor_takes))
            .where(Order.id == order_id, Order.client_id == user.id)
        )
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )

        if order.executor_takes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot edit order after executor has taken it",
            )

        if OrderService.is_expired(order):
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail="Order has expired"
            )

        if request.category:
            order.category = request.category
        if request.description:
            order.description = request.description
        if request.contact:
            order.contact = request.contact

        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def delete_order(db: AsyncSession, order_id: str, user: User) -> None:
        result = await db.execute(
            select(Order)
            .options(selectinload(Order.executor_takes))
            .where(Order.id == order_id, Order.client_id == user.id)
        )
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )

        if order.executor_takes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete order after executor has taken it",
            )

        order.status = OrderStatus.DELETED

        # Update counter
        user.active_orders_count = max(0, user.active_orders_count - 1)

        await db.commit()

    @staticmethod
    async def get_order(
        db: AsyncSession, order_id: str, user: User | None = None
    ) -> tuple[Order, bool]:
        """Returns (order, show_contact). Does NOT mutate the ORM object."""
        result = await db.execute(
            select(Order)
            .options(selectinload(Order.executor_takes))
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )

        show_contact = False
        if user:
            is_client = order.client_id == user.id
            is_executor_paid = any(
                take.executor_id == user.id for take in order.executor_takes
            )
            show_contact = is_client or is_executor_paid

        return order, show_contact

    @staticmethod
    async def list_orders(
        db: AsyncSession,
        category: str | None = None,
        city: str | None = None,
        status_filter: OrderStatus = OrderStatus.ACTIVE,
        limit: int = 50,
        offset: int = 0,
        client_id: int | None = None,
    ) -> tuple[list[Order], int]:
        """List orders. Does NOT mutate ORM objects — contact hiding is done in the route."""
        # Restrict to public statuses (skip restriction when filtering by owner)
        if not client_id and status_filter not in LISTABLE_STATUSES:
            status_filter = OrderStatus.ACTIVE

        query = select(Order).options(selectinload(Order.executor_takes))

        if client_id:
            query = query.where(Order.client_id == client_id)
        if status_filter:
            query = query.where(Order.status == status_filter)
        if category:
            query = query.where(Order.category == category)
        if city:
            query = query.where(Order.city == city)

        query = query.order_by(Order.created_at.desc())

        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query) or 0

        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        orders = list(result.scalars().all())

        return orders, total

    @staticmethod
    async def take_order(
        db: AsyncSession, order_id: str, executor: User
    ) -> tuple[str, int, int]:
        """
        Executor takes order (costs 2₽).
        Returns (contact, executor_count, new_balance).
        Locks both executor and order rows to prevent race conditions.
        """
        # Lock executor row to prevent concurrent balance races
        result = await db.execute(
            select(User).where(User.id == executor.id).with_for_update()
        )
        executor = result.scalar_one()

        # Lock order row
        result = await db.execute(
            select(Order)
            .options(selectinload(Order.executor_takes))
            .where(Order.id == order_id)
            .with_for_update()
        )
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )

        if order.status != OrderStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail="Order is no longer active"
            )

        if OrderService.is_expired(order):
            order.status = OrderStatus.EXPIRED
            # Update client counter
            client_result = await db.execute(
                select(User).where(User.id == order.client_id)
            )
            client = client_result.scalar_one_or_none()
            if client:
                client.active_orders_count = max(0, client.active_orders_count - 1)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail="Order has expired"
            )

        # Prevent client from taking own order
        if order.client_id == executor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot take your own order",
            )

        # Already taken by this executor — return contact without charging
        if any(take.executor_id == executor.id for take in order.executor_takes):
            return order.contact, len(order.executor_takes), executor.balance

        # Max executors check
        if len(order.executor_takes) >= settings.max_executors_per_order:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Maximum {settings.max_executors_per_order} executors reached",
            )

        # Balance check (on locked row — safe from races)
        if executor.balance < settings.order_take_cost:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient balance. Need {settings.order_take_cost}₽",
            )

        # Deduct balance and update counter
        executor.balance -= settings.order_take_cost
        executor.active_orders_count += 1

        # Create executor take
        take = ExecutorTake(order_id=order.id, executor_id=executor.id)
        db.add(take)

        # Log transaction
        transaction = BalanceTransaction(
            user_id=executor.id,
            type=TransactionType.ORDER_TAKE,
            amount=-settings.order_take_cost,
            balance_after=executor.balance,
            order_id=order.id,
            description=f"Took order {order.id}",
        )
        db.add(transaction)

        await db.commit()
        await db.refresh(order, ["executor_takes"])

        return order.contact, len(order.executor_takes), executor.balance

    @staticmethod
    async def respond_to_order(
        db: AsyncSession, order_id: str, user: User
    ) -> Order:
        """Client confirms they responded to executor contact."""
        result = await db.execute(
            select(Order)
            .options(selectinload(Order.executor_takes))
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )

        if order.client_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the order client can respond",
            )

        if order.status != OrderStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail="Order is no longer active"
            )

        if not order.executor_takes:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No executor has taken this order yet",
            )

        if order.customer_responded_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already responded",
            )

        order.customer_responded_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(order, ["executor_takes"])
        return order

    @staticmethod
    async def close_order(
        db: AsyncSession, order_id: str, user: User
    ) -> None:
        """Client closes order without completion (e.g. no longer needed)."""
        result = await db.execute(
            select(Order)
            .options(selectinload(Order.executor_takes))
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )

        if order.client_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the order client can close it",
            )

        if order.status != OrderStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail="Order is no longer active"
            )

        if not order.executor_takes:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No executor has taken this order yet",
            )

        order.status = OrderStatus.CLOSED_NO_RESPONSE
        user.active_orders_count = max(0, user.active_orders_count - 1)

        # Decrement executor counters
        for take in order.executor_takes:
            executor_result = await db.execute(
                select(User).where(User.id == take.executor_id)
            )
            executor = executor_result.scalar_one_or_none()
            if executor:
                executor.active_orders_count = max(0, executor.active_orders_count - 1)

        await db.commit()

    @staticmethod
    async def complete_order(
        db: AsyncSession, order_id: str, user: User
    ) -> Order:
        """Client marks order as completed."""
        result = await db.execute(
            select(Order)
            .options(selectinload(Order.executor_takes))
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )

        if order.client_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the order client can complete it",
            )

        if order.status != OrderStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail="Order is no longer active"
            )

        if not order.executor_takes:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No executor has taken this order yet",
            )

        order.status = OrderStatus.COMPLETED
        user.active_orders_count = max(0, user.active_orders_count - 1)
        user.completed_orders_count += 1

        # Update executor counters
        for take in order.executor_takes:
            executor_result = await db.execute(
                select(User).where(User.id == take.executor_id)
            )
            executor = executor_result.scalar_one_or_none()
            if executor:
                executor.active_orders_count = max(0, executor.active_orders_count - 1)
                executor.completed_orders_count += 1

        await db.commit()
        await db.refresh(order, ["executor_takes"])
        return order
