"""Data models for the RepoRescue Checkout Service."""

from typing import List, Optional
from pydantic import BaseModel, Field


class Item(BaseModel):
    item_id: str = Field(..., description="Unique product identifier")
    name: str = Field(..., description="Product name")
    unit_price: float = Field(..., gt=0, description="Price per unit in USD")
    quantity: int = Field(..., gt=0, description="Quantity ordered")


class ShippingAddress(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str
    country: str = "US"


class PaymentMethod(BaseModel):
    method_type: str = Field(..., description="Payment method: credit_card, paypal, store_credit")
    card_last4: Optional[str] = Field(None, description="Last 4 digits if credit_card")


class CheckoutRequest(BaseModel):
    customer_id: str = Field(..., description="Customer unique ID")
    items: List[Item] = Field(..., min_length=1, description="List of items to purchase")
    shipping_address: ShippingAddress
    payment_method: PaymentMethod
    promo_code: Optional[str] = Field(None, description="Optional promotional discount code")


class CheckoutResponse(BaseModel):
    order_id: str
    customer_id: str
    status: str
    subtotal: float
    discount_amount: float
    promo_code: Optional[str]
    tax_amount: float
    total_amount: float
    item_count: int
    message: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
