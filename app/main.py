"""Main FastAPI application entry point for RepoRescue Checkout Service."""

from fastapi import FastAPI, status
from app.models import CheckoutRequest, CheckoutResponse, HealthResponse
from app.service import process_checkout, ACTIVE_PROMOTIONS

app = FastAPI(
    title="RepoRescue Checkout Service",
    description="FastAPI Checkout Service for Flip the Switch Hackathon 2026",
    version="1.0.0"
)


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check() -> HealthResponse:
    """Service health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="checkout-service",
        version="1.0.0"
    )


@app.get("/promotions", tags=["Promotions"])
def list_promotions():
    """List available active promotional codes."""
    return {
        "promotions": [
            {"code": code, "description": data["description"]}
            for code, data in ACTIVE_PROMOTIONS.items()
        ]
    }


@app.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_200_OK,
    tags=["Checkout"]
)
def checkout(request: CheckoutRequest) -> CheckoutResponse:
    """Process an order checkout request.

    Note: Sending promo_code='RESCUE20' triggers the seeded bug (BUG-001),
    causing an unhandled KeyError which results in an HTTP 500 response.
    """
    return process_checkout(request)
