from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.order import OrderStatus
from app.models.user import User
from app.schemas.order import (
    CreateOrderRequest,
    ExecutorTakeResponse,
    OrderDetailResponse,
    OrderListResponse,
    OrderResponse,
    UpdateOrderRequest,
)
from app.services.notification_service import notify_new_order
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    request: CreateOrderRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Create new order (FREE for clients)"""
    order = await OrderService.create_order(db, user, request)
    background_tasks.add_task(notify_new_order, order.id, order.category, order.city, order.client_id)
    return OrderResponse.model_validate(order)


@router.get("", response_model=OrderListResponse)
async def list_orders(
    category: str | None = Query(None),
    city: str | None = Query(None),
    status: OrderStatus = Query(OrderStatus.ACTIVE),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    mine: bool = Query(False),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> OrderListResponse:
    """List orders with filters (no auth required for browsing)"""
    client_id = user.id if mine and user else None
    orders, total = await OrderService.list_orders(db, category, city, status, limit, offset, client_id=client_id)
    # Hide contacts in list view — build response without mutating ORM objects
    responses = []
    for o in orders:
        resp = OrderResponse.model_validate(o)
        resp.contact = None
        responses.append(resp)
    return OrderListResponse(orders=responses, total=total)


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: str,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> OrderDetailResponse:
    """Get order details (contact visible after payment)"""
    order, show_contact = await OrderService.get_order(db, order_id, user)
    resp = OrderDetailResponse.model_validate(order)
    if not show_contact:
        resp.contact = None
    return resp


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: str,
    request: UpdateOrderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Update order (only before executor takes it, city locked)"""
    order = await OrderService.update_order(db, order_id, user, request)
    return OrderResponse.model_validate(order)


@router.delete("/{order_id}", status_code=204)
async def delete_order(
    order_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete order (only before executor takes it)"""
    await OrderService.delete_order(db, order_id, user)


@router.post("/{order_id}/take", response_model=ExecutorTakeResponse)
async def take_order(
    order_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExecutorTakeResponse:
    """Executor takes order (costs 2₽, max 3 executors)"""
    contact, executor_count, new_balance = await OrderService.take_order(db, order_id, user)
    return ExecutorTakeResponse(
        success=True,
        contact=contact,
        executor_count=executor_count,
        new_balance=new_balance,
    )


@router.post("/{order_id}/respond", response_model=OrderResponse)
async def respond_to_order(
    order_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Client confirms they responded to executor contact"""
    order = await OrderService.respond_to_order(db, order_id, user)
    return OrderResponse.model_validate(order)


@router.post("/{order_id}/close", status_code=204)
async def close_order(
    order_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Client closes order (no longer needed, after executor took it)"""
    await OrderService.close_order(db, order_id, user)


@router.post("/{order_id}/complete", response_model=OrderResponse)
async def complete_order(
    order_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Client marks order as completed"""
    order = await OrderService.complete_order(db, order_id, user)
    return OrderResponse.model_validate(order)
