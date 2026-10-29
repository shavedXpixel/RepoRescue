"""Pytest fixtures for RepoRescue checkout tests."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client configured to receive HTTP 500 status codes for unhandled exceptions.

    Using raise_server_exceptions=False mimics real HTTP client behavior (like Discord bot,
    cURL, or web frontend), allowing tests to assert against HTTP 500 status responses.
    """
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def sample_checkout_payload():
    """Standard valid checkout payload without promotional codes."""
    return {
        "customer_id": "cust_demo_001",
        "items": [
            {
                "item_id": "prod_keyboard_01",
                "name": "Mechanical Gaming Keyboard",
                "unit_price": 100.0,
                "quantity": 1
            },
            {
                "item_id": "prod_mouse_02",
                "name": "Ergonomic Wireless Mouse",
                "unit_price": 50.0,
                "quantity": 1
            }
        ],
        "shipping_address": {
            "street": "123 Hackathon Way",
            "city": "Austin",
            "state": "TX",
            "zip_code": "78701",
            "country": "US"
        },
        "payment_method": {
            "method_type": "credit_card",
            "card_last4": "4242"
        }
    }
