"""
Sprint 3 - Concurrency stress tests
Ten buyers compete for the same product. Under PostgreSQL, requests run in parallel
(ThreadPoolExecutor). SQLite (used in this module's in-memory fixture and in CI) does not
reliably serialize concurrent writes, so we run the same HTTP sequence sequentially there.
"""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models import Base, Product, WalletLedger, Transaction
from app.services.state_machine import ProductState


@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield engine
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_verify_token(monkeypatch):
    def verify_token(token):
        if token.startswith("valid-token-"):
            return token.replace("valid-token-", "")
        return None

    from app.api import deps

    monkeypatch.setattr(deps, "verify_token", verify_token)


def _sqlite_engine(test_db) -> bool:
    return "sqlite" in str(test_db.url).lower()


def _run_buy_attempts(test_db, product_id: int, num_buyers: int) -> list[int]:
    """Parallel on Postgres; sequential on SQLite (avoids double-commit races)."""
    if _sqlite_engine(test_db) and os.getenv("FORCE_THREAD_STRESS", "").lower() not in ("1", "true", "yes"):
        return [_buy_worker(product_id, i) for i in range(num_buyers)]
    with ThreadPoolExecutor(max_workers=num_buyers) as pool:
        futures = [pool.submit(_buy_worker, product_id, i) for i in range(num_buyers)]
        return [f.result() for f in as_completed(futures)]


def _run_reserve_attempts(test_db, product_id: int, num_buyers: int) -> list[int]:
    if _sqlite_engine(test_db) and os.getenv("FORCE_THREAD_STRESS", "").lower() not in ("1", "true", "yes"):
        return [_reserve_worker(product_id, i) for i in range(num_buyers)]
    with ThreadPoolExecutor(max_workers=num_buyers) as pool:
        futures = [pool.submit(_reserve_worker, product_id, i) for i in range(num_buyers)]
        return [f.result() for f in as_completed(futures)]


def _buy_worker(product_id: int, buyer_index: int) -> int:
    with TestClient(app) as local_client:
        headers = {"Authorization": f"Bearer valid-token-buyer-stress-{buyer_index}"}
        response = local_client.post(f"/products/{product_id}/buy", headers=headers)
        return response.status_code


def _reserve_worker(product_id: int, buyer_index: int) -> int:
    with TestClient(app) as local_client:
        headers = {"Authorization": f"Bearer valid-token-reserver-{buyer_index}"}
        response = local_client.post(f"/products/{product_id}/reserve", headers=headers)
        return response.status_code


def test_concurrent_purchase_stress(test_db, mock_verify_token):
    """
    Ten buyers race to purchase the same available product.
    Exactly one must succeed (201); the others must fail with a client error (e.g. 400).
    """
    NUM_BUYERS = 10
    PRODUCT_PRICE = 50.0
    INITIAL_BALANCE = 200.0

    SessionLocal = sessionmaker(bind=test_db)
    db = SessionLocal()

    product = Product(
        title="Stress Test Item",
        description="Solo uno puede comprarme",
        category="Test",
        price=PRODUCT_PRICE,
        state=ProductState.AVAILABLE,
        owner_id="seller-stress",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    product_id = product.id

    for i in range(NUM_BUYERS):
        ledger = WalletLedger(
            user_id=f"buyer-stress-{i}",
            amount=INITIAL_BALANCE,
            transaction_type="TOP_UP",
            description="Fondos iniciales",
            balance_after=INITIAL_BALANCE,
        )
        db.add(ledger)
    db.commit()
    db.close()

    results = _run_buy_attempts(test_db, product_id, NUM_BUYERS)

    successful = results.count(201)
    failed = [r for r in results if r != 201]

    assert successful == 1, f"Expected exactly one 201, got {successful}. Results: {results}"
    assert len(failed) == NUM_BUYERS - 1
    for code in failed:
        assert code in (400, 402), f"Unexpected failure status: {code}"

    db2 = SessionLocal()
    final_product = db2.query(Product).filter(Product.id == product_id).first()
    assert final_product.state == ProductState.SOLD

    tx_count = db2.query(Transaction).filter(Transaction.product_id == product_id).count()
    assert tx_count == 1, f"Expected 1 transaction row, found {tx_count}"
    db2.close()


def test_concurrent_reservation_stress(test_db, mock_verify_token):
    """
    Ten buyers race to reserve the same product.
    Exactly one must succeed (200); others get 409 (already reserved) or 400 (invalid transition).
    """
    NUM_BUYERS = 10

    SessionLocal = sessionmaker(bind=test_db)
    db = SessionLocal()

    product = Product(
        title="Reservation Stress Item",
        description="Solo uno puede reservarme",
        category="Test",
        price=100.0,
        state=ProductState.AVAILABLE,
        owner_id="seller-stress-2",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    product_id = product.id
    db.close()

    results = _run_reserve_attempts(test_db, product_id, NUM_BUYERS)

    successful = results.count(200)
    assert successful == 1, f"Expected exactly one 200, got {successful}. Results: {results}"

    failed = [r for r in results if r != 200]
    assert len(failed) == NUM_BUYERS - 1
    for code in failed:
        assert code in (400, 409), f"Unexpected failure status: {code}"

    db2 = SessionLocal()
    final_product = db2.query(Product).filter(Product.id == product_id).first()
    assert final_product.state == ProductState.RESERVED
    db2.close()
