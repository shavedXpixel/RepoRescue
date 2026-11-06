"""Test suite for RepoRescue Checkout Service.

================================================================================
IMPORTANT NOTICE FOR HACKATHON EVALUATORS & AGENTS:
- Normal checkout tests verify standard functionality (Health, standard checkout,
  fixed promotions, and invalid promo code validation).
- 'test_reproduce_bug_001_checkout_with_rescue20_promo' is the DELIBERATELY SEEDED
  BUG REPRODUCTION TEST. It is EXPECTED TO FAIL with HTTP 500 during this milestone.
================================================================================
"""

import pytest
from fastapi import HTTPException
from app.service import apply_discount, ACTIVE_PROMOTIONS


# ------------------------------------------------------------------------------
# Normal Checkout Behavior Tests (All expected to PASS)
# ------------------------------------------------------------------------------

def test_health_endpoint(client):
    """Verify that the health check endpoint returns 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "checkout-service"


def test_checkout_standard_order_success(client, sample_checkout_payload):
    """Verify standard checkout without promotional codes succeeds with 200 OK."""
    response = client.post("/checkout", json=sample_checkout_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "confirmed"
    assert data["subtotal"] == 150.00
    assert data["discount_amount"] == 0.00
    assert data["tax_amount"] == 12.00  # 8% of 150.00
    assert data["total_amount"] == 162.00
    assert data["item_count"] == 2
    assert data["order_id"].startswith("ord_")


def test_checkout_with_valid_fixed_discount_promo(client, sample_checkout_payload):
    """Verify that a valid fixed-value promo code (SAVE10) correctly applies $10 off."""
    payload = dict(sample_checkout_payload)
    payload["promo_code"] = "SAVE10"

    response = client.post("/checkout", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "confirmed"
    assert data["subtotal"] == 150.00
    assert data["discount_amount"] == 10.00
    # Taxable is 140.00, 8% tax = 11.20
    assert data["tax_amount"] == 11.20
    assert data["total_amount"] == 151.20


def test_checkout_with_invalid_promo_code_returns_400(client, sample_checkout_payload):
    """Verify that an unknown promo code returns HTTP 400 Bad Request."""
    payload = dict(sample_checkout_payload)
    payload["promo_code"] = "NONEXISTENT_CODE"

    response = client.post("/checkout", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "Invalid promo code" in data["detail"]


def test_checkout_validation_empty_items_returns_422(client):
    """Verify that checkout request with empty items fails validation with 422."""
    payload = {
        "customer_id": "cust_invalid",
        "items": [],
        "shipping_address": {
            "street": "1 Main St",
            "city": "Austin",
            "state": "TX",
            "zip_code": "78701",
            "country": "US"
        },
        "payment_method": {
            "method_type": "credit_card"
        }
    }
    response = client.post("/checkout", json=payload)
    assert response.status_code == 422


# ------------------------------------------------------------------------------
# Deliberately Seeded Bug Reproduction Test (EXPECTED TO FAIL)
# ------------------------------------------------------------------------------

def test_reproduce_bug_001_checkout_with_rescue20_promo(client, sample_checkout_payload):
    """
    ============================================================================
    BUG REPRODUCTION TEST: BUG-001 (EXPECTED TO FAIL)
    ============================================================================
    Target:
        POST /checkout with promo_code="RESCUE20"

    Expected Behavior:
        HTTP 200 OK with:
        - Subtotal: $150.00
        - 20% Discount: $30.00
        - Taxable: $120.00
        - Tax (8%): $9.60
        - Total: $129.60

    Actual Seeded Behavior:
        Returns HTTP 500 Internal Server Error because app/service.py looks up
        promo['discount_percent'] instead of promo['rate'], raising KeyError.

    Failure Assertion:
        `assert response.status_code == 200` fails with `500 == 200`.
    ============================================================================
    """
    payload = dict(sample_checkout_payload)
    payload["promo_code"] = "RESCUE20"

    response = client.post("/checkout", json=payload)

    # THIS ASSERTION IS EXPECTED TO FAIL DUE TO THE SEEDED BUG:
    assert response.status_code == 200, (
        f"Seeded bug BUG-001 reproduced: Expected HTTP 200, but received HTTP {response.status_code}. "
        f"Response body: {response.text}"
    )

    data = response.json()
    assert data["status"] == "confirmed"
    assert data["subtotal"] == 150.00
    assert data["discount_amount"] == 30.00
    assert data["tax_amount"] == 9.60
    assert data["total_amount"] == 129.60


# ------------------------------------------------------------------------------
# Focused Unit Tests for apply_discount (BUG-001 Coverage & Boundary Testing)
# ------------------------------------------------------------------------------

def test_apply_discount_rescue20_exact_amount():
    """Verify apply_discount independently for RESCUE20 (rate 0.20).

    Verifies the exact discount amount for known subtotals and confirms that
    a 0.20 rate produces a 20% discount, not 0.2%.
    """
    # Known subtotal $150.00 -> 20% discount = $30.00
    discount_150 = apply_discount(150.00, "RESCUE20")
    assert discount_150 == 30.00
    assert discount_150 != 0.30  # Guard against erroneous /100.0 division (0.2%)

    # Known subtotal $100.00 -> 20% discount = $20.00
    discount_100 = apply_discount(100.00, "RESCUE20")
    assert discount_100 == 20.00

    # Known subtotal $49.99 with rounding -> 49.99 * 0.20 = 9.998 -> $10.00
    discount_49_99 = apply_discount(49.99, "RESCUE20")
    assert discount_49_99 == 10.00


def test_apply_discount_case_and_whitespace_insensitivity():
    """Verify that apply_discount handles lowercase and surrounding whitespace."""
    assert apply_discount(100.00, "  rescue20  ") == 20.00
    assert apply_discount(100.00, "rescue20") == 20.00


def test_apply_discount_percentage_boundary_rate_zero(monkeypatch):
    """Verify percentage calculation boundary condition for rate = 0 (0% discount).

    Under promotion rules, rate=0.0 is a valid lower boundary producing $0.00 discount.
    """
    monkeypatch.setitem(
        ACTIVE_PROMOTIONS,
        "ZERO_DISCOUNT",
        {"code": "ZERO_DISCOUNT", "type": "percentage", "rate": 0.0, "description": "0% off"}
    )
    assert apply_discount(150.00, "ZERO_DISCOUNT") == 0.00


def test_apply_discount_percentage_boundary_rate_one(monkeypatch):
    """Verify percentage calculation boundary condition for rate = 1 (100% discount).

    Under promotion rules, rate=1.0 is a valid upper boundary producing a 100% discount
    equal to the entire subtotal.
    """
    monkeypatch.setitem(
        ACTIVE_PROMOTIONS,
        "FULL_DISCOUNT",
        {"code": "FULL_DISCOUNT", "type": "percentage", "rate": 1.0, "description": "100% off"}
    )
    assert apply_discount(150.00, "FULL_DISCOUNT") == 150.00


def test_apply_discount_subtotal_zero_boundary():
    """Verify that apply_discount with subtotal = 0.0 returns 0.00 discount."""
    assert apply_discount(0.0, "RESCUE20") == 0.00


def test_apply_discount_none_or_empty_code():
    """Verify that apply_discount returns 0.00 when promo_code is None or empty string."""
    assert apply_discount(100.00, None) == 0.00
    assert apply_discount(100.00, "") == 0.00


def test_apply_discount_invalid_code_raises_http_400():
    """Verify that apply_discount raises HTTPException 400 for unknown promo code."""
    with pytest.raises(HTTPException) as exc_info:
        apply_discount(100.00, "NONEXISTENT_PROMO")
    assert exc_info.value.status_code == 400
    assert "Invalid promo code" in exc_info.value.detail
