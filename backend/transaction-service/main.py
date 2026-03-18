"""
Main entry point for the Transaction Service.
Initializes the FastAPI application, creates database tables,
and registers all routers.
"""

from fastapi import FastAPI
from app.database import engine
from app.models import Base
from app.routers import products

# Create SQL tables if they don't exist
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Transaction Service",
    description="Handles product state transitions and transaction history for Wallabot.",
    version="1.0.0"
)

# ── Routers ──────────────────────────────────
#Register all the endpoints of products.py
app.include_router(products.router)


# ── Health Check ─────────────────────────────
#Dockers endpoint to check if the service is alive
@app.get("/health", tags=["health"])
def health_check():
    """Returns service status. Used by Docker healthcheck."""
    return {"status": "ok", "service": "transaction-service"}