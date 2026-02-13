from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user, get_optional_user
from app.models.user import User
from app.schemas.review import (
    ClientReviewRequest,
    ClientReviewResponse,
    ExecutorComplaintRequest,
    ReviewCheckResponse,
    ReviewResponse,
)
from app.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get("/check", response_model=ReviewCheckResponse)
async def check_review(
    order_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewCheckResponse:
    """Check if user already submitted a review or complaint for an order"""
    submitted, review_type = await ReviewService.check_review_exists(db, user.id, order_id)
    return ReviewCheckResponse(submitted=submitted, type=review_type)


@router.post("/client", response_model=ClientReviewResponse)
async def create_client_review(
    request: ClientReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClientReviewResponse:
    """Client leaves review for executor (1-5 stars)"""
    review_id = await ReviewService.create_client_review(db, user, request)
    return ClientReviewResponse(success=True, review_id=review_id)


@router.post("/executor", status_code=200)
async def create_executor_complaint(
    request: ExecutorComplaintRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool | int]:
    """Executor leaves complaint about client"""
    complaint_id = await ReviewService.create_executor_complaint(db, user, request)
    return {"success": True, "complaint_id": complaint_id}


@router.get("", response_model=list[ReviewResponse])
async def list_reviews(
    rating: int | None = Query(None, ge=1, le=5),
    limit: int = Query(50, ge=1, le=100),
    mine: bool = Query(False),
    about_me: bool = Query(False),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> list[ReviewResponse]:
    """List reviews with optional rating/author/subject filter"""
    client_id = user.id if mine and user else None
    executor_id = user.id if about_me and user else None
    reviews = await ReviewService.list_reviews(
        db, rating, limit, client_id=client_id, executor_id=executor_id
    )

    # Transform to response format (data already eager-loaded)
    response = []
    for review in reviews:
        response.append(
            ReviewResponse(
                id=review.id,
                author_name=review.executor.first_name if review.executor else "Unknown",
                rating=review.rating,
                comment=review.comment,
                category=review.order.category if review.order else "Unknown",
                created_at=review.created_at,
            )
        )

    return response
