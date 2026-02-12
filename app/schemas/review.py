from datetime import datetime

from pydantic import BaseModel, Field

from app.models.review import ComplaintReason


class ClientReviewRequest(BaseModel):
    order_id: str
    executor_id: int | None = Field(None, description="ID of executor to review (auto-resolved if omitted)")
    rating: int = Field(ge=1, le=5, description="Rating from 1 to 5 stars")
    comment: str | None = Field(None, max_length=500)


class ClientReviewResponse(BaseModel):
    success: bool
    review_id: int


class ExecutorComplaintRequest(BaseModel):
    order_id: str
    complaint: ComplaintReason
    comment: str | None = Field(None, max_length=500)


class ReviewResponse(BaseModel):
    id: int
    author_name: str
    rating: int
    comment: str | None
    category: str
    created_at: datetime

    class Config:
        from_attributes = True
