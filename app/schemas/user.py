from pydantic import BaseModel, Field


class TelegramUser(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None


class TelegramInitData(BaseModel):
    init_data: str = Field(description="Raw initData string from Telegram WebApp SDK")


class UserProfileResponse(BaseModel):
    id: int
    first_name: str
    last_name: str | None
    username: str | None
    completed_orders: int
    active_orders: int
    rating: float
    balance: int

    class Config:
        from_attributes = True


class UpdatePreferencesRequest(BaseModel):
    categories: list[str] = Field(default_factory=list, max_length=10)
    cities: list[str] = Field(default_factory=list, max_length=20)


class UpdateNotificationSettingsRequest(BaseModel):
    enabled: bool | None = Field(None, description="Enable or disable notifications")
    frequency: int | None = Field(None, ge=5, le=15, description="Notification frequency in minutes")


class NotificationSettingsResponse(BaseModel):
    enabled: bool
    frequency: int


class PreferencesResponse(BaseModel):
    categories: list[str]
    cities: list[str]
