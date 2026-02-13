import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import balance, cities, orders, reviews, users
from app.core.config import settings
from app.core.database import async_session_maker, engine
from app.models import (  # noqa
    BalanceTransaction,
    ClientReview,
    ExecutorComplaint,
    Order,
    PaymentInvoice,
    User,
)
from app.utils.timer import auto_close_expired_orders

logger = logging.getLogger(__name__)


async def _timer_loop() -> None:
    """Background loop that auto-closes expired orders every 60 seconds."""
    while True:
        try:
            async with async_session_maker() as db:
                await auto_close_expired_orders(db)
        except Exception:
            logger.exception("Timer loop error")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Startup and shutdown events"""
    logging.basicConfig(level=logging.INFO if not settings.debug else logging.DEBUG)
    logger.info("Срочные Услуги API starting...")
    logger.info(
        "Database: %s",
        settings.database_url.split("@")[1] if "@" in settings.database_url else "configured",
    )
    logger.info("Timer: %d minutes per order", settings.order_lifetime_minutes)
    logger.info("Cost: %d₽ per order access", settings.order_take_cost)

    timer_task = asyncio.create_task(_timer_loop())

    yield

    timer_task.cancel()
    try:
        await timer_task
    except asyncio.CancelledError:
        pass
    await engine.dispose()
    logger.info("API shutdown complete")


app = FastAPI(
    title="Срочные Услуги API",
    description="FastAPI backend for Telegram WebApp urgent services marketplace",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Routes
app.include_router(orders.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(balance.router, prefix=settings.api_prefix)
app.include_router(reviews.router, prefix=settings.api_prefix)
app.include_router(cities.router, prefix=settings.api_prefix)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "Срочные Услуги API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check() -> dict[str, str] | JSONResponse:
    try:
        async with async_session_maker() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unhealthy"})
