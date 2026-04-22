"""
Main entry point for the Transaction Service.
Initializes the FastAPI application and registers all routers.
Tables are managed directly in Supabase via SQL scripts.
"""

from fastapi import FastAPI
from app.routers import products, wallet, transactions

# Initialize FastAPI app
app = FastAPI(
    title="Transaction Service",
    description="Handles product state transitions and transaction history for Wallabot.",
    version="1.0.0"
)

# ── Routers ──────────────────────────────────
# Register all the endpoints
app.include_router(products.router)
app.include_router(wallet.router)
app.include_router(transactions.router)


# ── Health Check ─────────────────────────────
# Docker endpoint to check if the service is alive
@app.get("/health", tags=["health"])
def health_check():
    """Returns service status. Used by Docker healthcheck."""
    return {"status": "ok", "service": "transaction-service"}