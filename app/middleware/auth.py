import hashlib
import hmac
import json
from typing import Any
from urllib.parse import parse_qs

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

security = HTTPBearer()


def validate_telegram_init_data(init_data: str, bot_token: str) -> dict[str, Any]:
    """
    Validates Telegram WebApp initData according to official docs:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        parsed = parse_qs(init_data)

        # Extract hash from initData
        received_hash = parsed.get("hash", [None])[0]
        if not received_hash:
            raise ValueError("Missing hash in initData")

        # Remove hash from data for validation
        data_check_arr = []
        for key, values in sorted(parsed.items()):
            if key != "hash":
                data_check_arr.append(f"{key}={values[0]}")

        data_check_string = "\n".join(data_check_arr)

        # Generate secret key
        secret_key = hmac.new(
            "WebAppData".encode(), bot_token.encode(), hashlib.sha256
        ).digest()

        # Calculate hash
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if calculated_hash != received_hash:
            raise ValueError("Invalid hash - data integrity check failed")

        # Parse user data
        user_data: dict[str, Any] = json.loads(parsed.get("user", ["{}"])[0])
        if not user_data:
            raise ValueError("Missing user data in initData")

        return user_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Telegram initData: {str(e)}",
        ) from e


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates Telegram WebApp initData and returns or creates user.
    Token format: Bearer <initData>
    """
    init_data = credentials.credentials

    # Validate initData with bot token
    user_data = validate_telegram_init_data(init_data, settings.telegram_bot_token)

    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in initData",
        )

    # Get or create user
    result = await db.execute(select(User).where(User.id == telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=telegram_id,
            username=user_data.get("username"),
            first_name=user_data.get("first_name", ""),
            last_name=user_data.get("last_name"),
            language_code=user_data.get("language_code"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Optional authentication - returns None if no valid token"""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException as e:
        if e.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
            return None
        raise
