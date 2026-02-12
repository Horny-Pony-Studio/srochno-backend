from pydantic import BaseModel, Field


class CreateInvoiceRequest(BaseModel):
    amount: int = Field(ge=1, le=100000, description="Amount in rubles")


class CreateInvoiceResponse(BaseModel):
    payment_id: int
    pay_url: str
    mini_app_invoice_url: str | None = None


class PaymentStatusResponse(BaseModel):
    payment_id: int
    status: str  # "pending" | "paid" | "expired"
    amount: int
    new_balance: int | None = None
