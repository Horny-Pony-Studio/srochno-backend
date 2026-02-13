from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import ExecutorTake, Order, OrderStatus
from app.models.review import ClientReview, ExecutorComplaint
from app.models.user import User
from app.schemas.review import ClientReviewRequest, ExecutorComplaintRequest


class ReviewService:
    @staticmethod
    async def create_client_review(
        db: AsyncSession, user: User, request: ClientReviewRequest
    ) -> int:
        """Client leaves review for executor"""
        result = await db.execute(
            select(Order)
            .options(selectinload(Order.executor_takes))
            .where(Order.id == request.order_id, Order.client_id == user.id)
        )
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found or you are not the client",
            )

        if order.status not in [OrderStatus.COMPLETED, OrderStatus.EXPIRED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only review completed or expired orders",
            )

        # Auto-resolve executor_id from order takes if not provided
        executor_id = request.executor_id
        if executor_id is None:
            if not order.executor_takes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No executor has taken this order",
                )
            executor_id = order.executor_takes[0].executor_id

        # Verify the target executor actually took this order
        result = await db.execute(
            select(ExecutorTake).where(
                ExecutorTake.order_id == request.order_id,
                ExecutorTake.executor_id == executor_id,
            )
        )
        take = result.scalar_one_or_none()
        if not take:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This executor did not take this order",
            )

        # Check if already reviewed this executor for this order
        result = await db.execute(
            select(ClientReview).where(
                ClientReview.order_id == request.order_id,
                ClientReview.client_id == user.id,
                ClientReview.executor_id == executor_id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already reviewed this executor for this order",
            )

        review = ClientReview(
            order_id=request.order_id,
            client_id=user.id,
            executor_id=executor_id,
            rating=request.rating,
            comment=request.comment,
        )
        db.add(review)
        await db.commit()
        await db.refresh(review)

        # Update executor's average rating
        await ReviewService._update_executor_rating(db, executor_id)

        return review.id

    @staticmethod
    async def create_executor_complaint(
        db: AsyncSession, user: User, request: ExecutorComplaintRequest
    ) -> int:
        """Executor leaves complaint about client"""
        result = await db.execute(
            select(ExecutorTake).where(
                ExecutorTake.order_id == request.order_id, ExecutorTake.executor_id == user.id
            )
        )
        take = result.scalar_one_or_none()

        if not take:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You did not take this order",
            )

        result = await db.execute(select(Order).where(Order.id == request.order_id))
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )

        result = await db.execute(
            select(ExecutorComplaint).where(
                ExecutorComplaint.order_id == request.order_id,
                ExecutorComplaint.executor_id == user.id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Already complained about this order"
            )

        complaint = ExecutorComplaint(
            order_id=request.order_id,
            executor_id=user.id,
            client_id=order.client_id,
            complaint=request.complaint,
            comment=request.comment,
        )
        db.add(complaint)
        await db.commit()
        await db.refresh(complaint)

        return complaint.id

    @staticmethod
    async def _update_executor_rating(db: AsyncSession, executor_id: int) -> None:
        """Recalculate executor's average rating"""
        from sqlalchemy import func

        result = await db.execute(
            select(func.avg(ClientReview.rating)).where(
                ClientReview.executor_id == executor_id
            )
        )
        avg_rating = result.scalar() or 0.0

        result = await db.execute(select(User).where(User.id == executor_id))
        executor = result.scalar_one_or_none()
        if executor:
            executor.average_rating = float(avg_rating)
            await db.commit()

    @staticmethod
    async def list_reviews(
        db: AsyncSession, rating_filter: int | None = None, limit: int = 50
    ) -> list[ClientReview]:
        """List all reviews with optional rating filter"""
        query = (
            select(ClientReview)
            .options(selectinload(ClientReview.order), selectinload(ClientReview.executor))
            .order_by(ClientReview.created_at.desc())
        )

        if rating_filter:
            query = query.where(ClientReview.rating == rating_filter)

        query = query.limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
