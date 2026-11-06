"""Checkout service business logic and promotion calculation.

NOTE: This file contains a deliberately seeded, reproducible checkout bug
for the RepoRescue hackathon demo. DO NOT fix this bug during initial scaffolding.
"""

import uuid
from typing import Dict, Any, Optional
from fastapi import HTTPException
from app.models import CheckoutRequest, CheckoutResponse


# Active promotional codes table
ACTIVE_PROMOTIONS: Dict[str, Dict[str, Any]] = {
    "SAVE10": {
        "code": "SAVE10",
        "type": "fixed",
        "discount_value": 10.0,
        "description": "$10 off total order"
    },
    "FREESHIP5": {
        "code": "FREESHIP5",
        "type": "fixed",
        "discount_value": 5.0,
        "description": "$5 shipping credit"
    },
    # Seeded bug context: RESCUE20 is configured with 'rate' (0.20 for 20%),
    # but the calculation routine below looks for 'discount_percent'.
    "RESCUE20": {
        "code": "RESCUE20",
        "type": "percentage",
        "rate": 0.20,
        "description": "20% off entire order"
    }
}

TAX_RATE = 0.08  # 8% standard sales tax


def apply_discount(subtotal: float, promo_code: Optional[str]) -> float:
    """Calculate the discount amount for a given subtotal and promo code.

    Raises:
        HTTPException(400): If the promo code is unrecognized.
        KeyError: Seeded bug when promo_code is 'RESCUE20' (causing HTTP 500).
    """
    if not promo_code:
        return 0.0

    normalized_code = promo_code.strip().upper()
    if normalized_code not in ACTIVE_PROMOTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid promo code: '{promo_code}'. Please check the code and try again."
        )

    promo = ACTIVE_PROMOTIONS[normalized_code]

    if promo["type"] == "fixed":
        discount = min(subtotal, float(promo["discount_value"]))
        return round(discount, 2)

    elif promo["type"] == "percentage":
        rate = promo["rate"]
        discount = subtotal * rate
        return round(discount, 2)

    return 0.0


def process_checkout(request: CheckoutRequest) -> CheckoutResponse:
    """Process a customer checkout request."""
    # 1. Calculate subtotal
    subtotal = sum(item.unit_price * item.quantity for item in request.items)
    subtotal = round(subtotal, 2)

    # 2. Apply discount (will crash with KeyError / 500 if promo_code == 'RESCUE20')
    discount = apply_discount(subtotal, request.promo_code)

    # 3. Calculate tax on post-discount amount
    taxable_amount = max(0.0, subtotal - discount)
    tax_amount = round(taxable_amount * TAX_RATE, 2)

    # 4. Total calculation
    total_amount = round(taxable_amount + tax_amount, 2)

    # 5. Generate confirmation
    order_id = f"ord_{uuid.uuid4().hex[:10]}"
    total_items = sum(item.quantity for item in request.items)

    return CheckoutResponse(
        order_id=order_id,
        customer_id=request.customer_id,
        status="confirmed",
        subtotal=subtotal,
        discount_amount=discount,
        promo_code=request.promo_code,
        tax_amount=tax_amount,
        total_amount=total_amount,
        item_count=total_items,
        message=f"Order {order_id} placed successfully."
    )

