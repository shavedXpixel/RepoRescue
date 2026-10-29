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
