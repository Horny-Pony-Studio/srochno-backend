import json
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.balance import BalanceResponse, RechargeRequest, RechargeResponse
from app.schemas.payment import CreateInvoiceRequest, CreateInvoiceResponse, PaymentStatusResponse
from app.services.balance_service import BalanceService
from app.services.crypto_payment_service import CryptoPaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/balance", tags=["Balance"])


@router.get("", response_model=BalanceResponse)
async def get_balance(user: User = Depends(get_current_user)) -> BalanceResponse:
    """Get current user balance"""
    return BalanceResponse(balance=user.balance)


@router.post("/recharge", response_model=RechargeResponse)
async def recharge_balance(
    request: RechargeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RechargeResponse:
    """
    Recharge balance (DEV MODE - directly adds balance).
    TODO: Integrate Telegram Stars or YuKassa payment.
    """
    new_balance, transaction_id = await BalanceService.recharge_balance(
        db, user, request.amount, request.method
    )
    return RechargeResponse(success=True, new_balance=new_balance, transaction_id=transaction_id)


# ─── Crypto Bot Payment ─────────────────────────────────


@router.post("/create-invoice", response_model=CreateInvoiceResponse)
async def create_invoice(
    request: CreateInvoiceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CreateInvoiceResponse:
    """Create a Crypto Bot fiat RUB invoice for balance recharge."""
    payment = await CryptoPaymentService.create_invoice(db, user, request.amount)
    return CreateInvoiceResponse(
        payment_id=payment.id,
        pay_url=payment.pay_url or "",
        mini_app_invoice_url=payment.mini_app_invoice_url,
    )


@router.get("/payment/{payment_id}/status", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentStatusResponse:
    """Poll payment status. Returns new_balance when paid."""
    invoice = await CryptoPaymentService.get_invoice_status(db, payment_id, user.id)
    new_balance = user.balance if invoice.status.value == "paid" else None
    return PaymentStatusResponse(
        payment_id=invoice.id,
        status=invoice.status.value,
        amount=invoice.amount,
        new_balance=new_balance,
    )


@router.post("/webhook/crypto-bot")
async def crypto_bot_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Process Crypto Bot webhook (invoice_paid events)."""
    body = await request.body()
    body_text = body.decode("utf-8")
    signature = request.headers.get("crypto-pay-api-signature", "")

    if not CryptoPaymentService.verify_webhook(body_text, signature):
        logger.warning("Webhook: invalid signature")
        return {"ok": False}

    data = json.loads(body_text)

    update_type = data.get("update_type")
    if update_type != "invoice_paid":
        logger.info("Webhook: ignoring update_type=%s", update_type)
        return {"ok": True}

    payload = data.get("payload", {})
    crypto_bot_invoice_id = payload.get("invoice_id")
    if not crypto_bot_invoice_id:
        logger.warning("Webhook: missing invoice_id in payload")
        return {"ok": False}

    await CryptoPaymentService.process_paid_invoice(db, crypto_bot_invoice_id)
    return {"ok": True}
