from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.user import (
    NotificationSettingsResponse,
    PreferencesResponse,
    UpdateNotificationSettingsRequest,
    UpdatePreferencesRequest,
    UserProfileResponse,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    user: User = Depends(get_current_user),
) -> UserProfileResponse:
    """Get current user profile"""
    return UserProfileResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        completed_orders=user.completed_orders_count,
        active_orders=user.active_orders_count,
        rating=user.average_rating,
        balance=user.balance,
    )


@router.get("/me/notification-settings", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    user: User = Depends(get_current_user),
) -> NotificationSettingsResponse:
    """Get current notification settings"""
    return NotificationSettingsResponse(
        enabled=user.notifications_enabled,
        frequency=user.notification_frequency_minutes,
    )


@router.get("/me/preferences", response_model=PreferencesResponse)
async def get_preferences(
    user: User = Depends(get_current_user),
) -> PreferencesResponse:
    """Get current notification preferences (categories & cities)"""
    return PreferencesResponse(
        categories=user.subscribed_categories,
        cities=user.subscribed_cities,
    )


@router.put("/me/preferences", status_code=200)
async def update_preferences(
    request: UpdatePreferencesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Update notification preferences (categories & cities)"""
    user.subscribed_categories = request.categories
    user.subscribed_cities = request.cities
    await db.commit()
    return {"success": True}


@router.put("/me/notification-settings", status_code=200)
async def update_notification_settings(
    request: UpdateNotificationSettingsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Update notification settings (enabled flag and/or frequency)"""
    if request.enabled is not None:
        user.notifications_enabled = request.enabled
    if request.frequency is not None:
        user.notification_frequency_minutes = request.frequency
    await db.commit()
    return {"success": True}
