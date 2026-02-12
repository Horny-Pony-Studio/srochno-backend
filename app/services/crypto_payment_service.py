import logging
from datetime import datetime, timezone
from hashlib import sha256
from hmac import HMAC

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aiocryptopay import AioCryptoPay, Networks

from app.core.config import settings
from app.models.balance import BalanceTransaction, TransactionType
from app.models.payment import InvoiceStatus, PaymentInvoice
from app.models.user import User

logger = logging.getLogger(__name__)


def _get_network() -> str:
    if settings.crypto_bot_network == "main":
        return Networks.MAIN_NET
    return Networks.TEST_NET


class CryptoPaymentService:
    @staticmethod
    async def create_invoice(db: AsyncSession, user: User, amount: int) -> PaymentInvoice:
        """Create a Crypto Bot fiat RUB invoice."""
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be positive"
            )

        if not settings.crypto_bot_api_token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment service not configured",
            )

        async with AioCryptoPay(
            token=settings.crypto_bot_api_token,
            network=_get_network(),
        ) as client:
            invoice = await client.create_invoice(
                currency_type="fiat",
                fiat="RUB",
                amount=amount,
                description=f"Пополнение баланса на {amount}₽",
                expires_in=1800,  # 30 minutes
            )

        payment = PaymentInvoice(
            user_id=user.id,
            crypto_bot_invoice_id=invoice.invoice_id,
            amount=amount,
            status=InvoiceStatus.PENDING,
            pay_url=invoice.bot_invoice_url,
            mini_app_invoice_url=invoice.mini_app_invoice_url,
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)

        logger.info(
            "Created invoice #%d for user %d, amount=%d RUB, crypto_bot_id=%d",
            payment.id, user.id, amount, invoice.invoice_id,
        )
        return payment

    @staticmethod
    async def process_paid_invoice(db: AsyncSession, crypto_bot_invoice_id: int) -> None:
        """Process a paid invoice from Crypto Bot webhook. Idempotent."""
        # Find invoice
        result = await db.execute(
            select(PaymentInvoice)
            .where(PaymentInvoice.crypto_bot_invoice_id == crypto_bot_invoice_id)
            .with_for_update()
        )
        invoice = result.scalar_one_or_none()

        if not invoice:
            logger.warning("Webhook: invoice not found for crypto_bot_id=%d", crypto_bot_invoice_id)
            return

        # Idempotency: skip if already paid
        if invoice.status == InvoiceStatus.PAID:
            logger.info("Webhook: invoice #%d already paid, skipping", invoice.id)
            return

        # Lock user row
        user_result = await db.execute(
            select(User).where(User.id == invoice.user_id).with_for_update()
        )
        user = user_result.scalar_one()

        # Credit balance
        user.balance += invoice.amount

        # Create balance transaction
        transaction = BalanceTransaction(
            user_id=user.id,
            type=TransactionType.RECHARGE,
            amount=invoice.amount,
            balance_after=user.balance,
            payment_method="crypto_bot",
            external_transaction_id=str(crypto_bot_invoice_id),
            description=f"Crypto Bot payment #{crypto_bot_invoice_id}",
        )
        db.add(transaction)
        await db.flush()

        # Update invoice
        invoice.status = InvoiceStatus.PAID
        invoice.balance_transaction_id = transaction.id
        invoice.paid_at = datetime.now(timezone.utc)

        await db.commit()
        logger.info(
            "Invoice #%d paid: user=%d, amount=%d, new_balance=%d",
            invoice.id, user.id, invoice.amount, user.balance,
        )

    @staticmethod
    def verify_webhook(body: str, signature: str) -> bool:
        """Verify Crypto Bot webhook signature using HMAC-SHA256."""
        if not settings.crypto_bot_api_token:
            return False

        token_hash = sha256(settings.crypto_bot_api_token.encode("UTF-8")).digest()
        expected = HMAC(
            key=token_hash, msg=body.encode("UTF-8"), digestmod=sha256
        ).hexdigest()
        return expected == signature

    @staticmethod
    async def get_invoice_status(
        db: AsyncSession, payment_id: int, user_id: int
    ) -> PaymentInvoice:
        """Get invoice status, scoped to user for security."""
        result = await db.execute(
            select(PaymentInvoice).where(
                PaymentInvoice.id == payment_id,
                PaymentInvoice.user_id == user_id,
            )
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
            )
        return invoice
