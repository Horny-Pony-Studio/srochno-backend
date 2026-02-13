import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.user import User

logger = logging.getLogger(__name__)


async def notify_new_order(order_id: str, category: str, city: str, client_id: int) -> None:
    """
    Send Telegram notifications to subscribed executors about a new order.
    Runs as a background task — all errors are logged, never propagated.
    """
    try:
        async with async_session_maker() as db:
            await _send_notifications(db, order_id, category, city, client_id)
    except Exception:
        logger.exception("Failed to send notifications for order %s", order_id)


async def _send_notifications(
    db: AsyncSession, order_id: str, category: str, city: str, client_id: int
) -> None:
    now = datetime.now(timezone.utc)

    # Find subscribed executors matching category + city, excluding the client
    result = await db.execute(
        select(User).where(
            User.notifications_enabled.is_(True),
            User.subscribed_categories.contains([category]),
            User.subscribed_cities.contains([city]),
            User.id != client_id,
        )
    )
    executors = list(result.scalars().all())

    if not executors:
        logger.info("No subscribed executors for order %s (cat=%s, city=%s)", order_id, category, city)
        return

    # Filter by notification frequency
    eligible = []
    for executor in executors:
        if executor.last_notified_at is not None:
            cooldown = executor.last_notified_at + timedelta(minutes=executor.notification_frequency_minutes)
            if now < cooldown:
                continue
        eligible.append(executor)

    if not eligible:
        logger.info("All %d executors for order %s are in cooldown", len(executors), order_id)
        return

    bot_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    text = f"🔔 Новый заказ в категории «{category}» в городе {city}!\n\nОткройте приложение, чтобы посмотреть детали."

    async with httpx.AsyncClient(timeout=10) as client:
        for executor in eligible:
            try:
                resp = await client.post(bot_url, json={
                    "chat_id": executor.id,
                    "text": text,
                })
                if resp.status_code == 200:
                    executor.last_notified_at = now
                else:
                    logger.warning(
                        "Telegram API returned %d for user %d: %s",
                        resp.status_code, executor.id, resp.text,
                    )
            except Exception:
                logger.exception("Failed to send notification to user %d", executor.id)

    await db.commit()
    logger.info("Notified %d executors about order %s", len(eligible), order_id)
