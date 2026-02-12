from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.order import OrderStatus

# Valid Russian service categories
VALID_CATEGORIES = [
    "Сантехника",
    "Электрика",
    "Бытовой ремонт",
    "Клининг",
    "Сборка/установка",
    "Бытовая техника",
    "Другое",
]


class CreateOrderRequest(BaseModel):
    category: str = Field(description="Service category")
    description: str = Field(min_length=20, max_length=1000, description="Order description")
    city: str = Field(min_length=2, max_length=100, description="Russian city name")
    contact: str = Field(
        min_length=3, max_length=100, description="Telegram @username or Russian phone"
    )

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in VALID_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(VALID_CATEGORIES)}")
        return v


class UpdateOrderRequest(BaseModel):
    category: str | None = None
    description: str | None = Field(None, min_length=20, max_length=1000)
    contact: str | None = Field(None, min_length=3, max_length=100)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(VALID_CATEGORIES)}")
        return v


class ExecutorTakeSchema(BaseModel):
    executor_id: int
    taken_at: datetime

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: str
    category: str
    description: str
    city: str
    contact: str | None = None  # Hidden unless executor paid
    created_at: datetime
    expires_in_minutes: int
    status: OrderStatus
    taken_by: list[ExecutorTakeSchema] = Field(default_factory=list, validation_alias="executor_takes")
    customer_responded_at: datetime | None = Field(None, validation_alias="customer_responded_at")
    city_locked: bool

    class Config:
        from_attributes = True
        populate_by_name = True


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int


class OrderDetailResponse(OrderResponse):
    pass


class ExecutorTakeResponse(BaseModel):
    success: bool
    contact: str
    executor_count: int
    new_balance: int
