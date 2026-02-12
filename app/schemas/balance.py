from pydantic import BaseModel, Field


class BalanceResponse(BaseModel):
    balance: int


class RechargeRequest(BaseModel):
    amount: int = Field(ge=1, le=100000, description="Amount in rubles")
    method: str = Field(default="telegram_stars", description="Payment method")


class RechargeResponse(BaseModel):
    success: bool
    new_balance: int
    transaction_id: int
