from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.balance import BalanceTransaction, TransactionType
from app.models.user import User


class BalanceService:
    @staticmethod
    async def recharge_balance(
        db: AsyncSession, user: User, amount: int, method: str = "telegram_stars"
    ) -> tuple[int, int]:
        """
        Recharge user balance. Returns (new_balance, transaction_id).
        In production, integrate with payment provider (Telegram Stars, YuKassa).
        """
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be positive"
            )

        # TODO: Integrate payment provider
        # For now, directly add to balance (DEV MODE)

        # Lock user row to prevent concurrent balance races
        result = await db.execute(
            select(User).where(User.id == user.id).with_for_update()
        )
        user = result.scalar_one()

        user.balance += amount

        transaction = BalanceTransaction(
            user_id=user.id,
            type=TransactionType.RECHARGE,
            amount=amount,
            balance_after=user.balance,
            payment_method=method,
            description=f"Balance recharge via {method}",
        )
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)

        return user.balance, transaction.id

    @staticmethod
    async def refund_order(
        db: AsyncSession, user: User, order_id: str, amount: int
    ) -> None:
        """Refund balance for order (e.g., auto-closed no response)"""
        user.balance += amount

        transaction = BalanceTransaction(
            user_id=user.id,
            type=TransactionType.REFUND,
            amount=amount,
            balance_after=user.balance,
            order_id=order_id,
            description=f"Refund for order {order_id}",
        )
        db.add(transaction)
