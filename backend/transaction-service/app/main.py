"""
Main entry point for the Transaction Service.
Initializes the FastAPI application and registers all routers.
Tables are managed directly in Supabase via SQL scripts.
"""

from fastapi import FastAPI
from threading import Lock
from sqlalchemy import inspect, text
from app.database import DATABASE_URL, engine
from app.models import Base
from app.routers import products, wallet, transactions

startup_lock = Lock()

# Initialize FastAPI app
app = FastAPI(
    title="Transaction Service",
    description="Handles product state transitions and transaction history for Wallabot.",
    version="1.0.0"
)


@app.on_event("startup")
def on_startup():
    if DATABASE_URL.startswith("sqlite"):
        with startup_lock:
            Base.metadata.create_all(bind=engine)
            with engine.begin() as conn:
                inspector = inspect(conn)
                existing_columns = {col["name"] for col in inspector.get_columns("transaction_products")}
                if "reserved_by" not in existing_columns:
                    conn.execute(
                        text("ALTER TABLE transaction_products ADD COLUMN reserved_by VARCHAR(255)")
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
