"""
Main entry point for the Transaction Service.
Initializes the FastAPI application and registers all routers.
Tables are managed directly in Supabase via SQL scripts.
"""

from contextlib import asynccontextmanager
import threading

from fastapi import FastAPI
from sqlalchemy import inspect, text

from app.database import DATABASE_URL, engine
from app.models import Base
from app.core.config import settings
from app.core.logging import configure_logging, get_logger

startup_lock = threading.Lock()


def _run_reservation_cleanup(stop: threading.Event) -> None:
    log = get_logger("reservation_cleanup")
    from app.database import SessionLocal
    from app.routers.transactions import release_expired_reservations

    interval = max(5, settings.RESERVATION_CLEANUP_INTERVAL_SECONDS)
    while not stop.is_set():
        db = SessionLocal()
        try:
            released = release_expired_reservations(db)
            if released:
                log.info("released_expired_reservations", released_count=released)
        except Exception:
            log.exception("reservation_cleanup_failed")
        finally:
            db.close()
        if stop.wait(interval):
            break


@asynccontextmanager
async def lifespan(app: FastAPI):
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

    cleanup_stop: threading.Event | None = None
    cleanup_thread: threading.Thread | None = None
    if settings.RESERVATION_CLEANUP_ENABLED:
        cleanup_stop = threading.Event()
        cleanup_thread = threading.Thread(
            target=_run_reservation_cleanup,
            args=(cleanup_stop,),
            daemon=True,
            name="reservation-cleanup",
        )
        cleanup_thread.start()

    yield

    if cleanup_stop is not None:
        cleanup_stop.set()
    if cleanup_thread is not None:
        cleanup_thread.join(timeout=10.0)


def _register_routers(application: FastAPI) -> None:
    from app.routers import products, wallet, transactions, test_cleanup
    from app.services.test_cleanup_service import is_test_cleanup_enabled

    application.include_router(products.router)
    application.include_router(wallet.router)
    application.include_router(transactions.router)
    if is_test_cleanup_enabled():
        application.include_router(test_cleanup.router)


configure_logging()

app = FastAPI(
    title="Transaction Service",
    description="Handles product state transitions and transaction history for Wallabot.",
    version="1.0.0",
    lifespan=lifespan,
)
_register_routers(app)


@app.get("/health", tags=["health"])
def health_check():
    """Returns service status. Used by Docker healthcheck."""
    return {"status": "ok", "service": "transaction-service"}
