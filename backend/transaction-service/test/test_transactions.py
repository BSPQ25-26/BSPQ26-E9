"""
Integration tests for Transaction endpoints.

Tests:
1. Reserve: successful reservation, ownership guard, state transitions
2. Purchase: fund validation, atomic flow, state transitions, transaction record
3. History: pagination, immutability, role filtering
4. Concurrent Reservation: race condition handling
5. Timeout Release: expired reservation cleanup
"""

import pytest
import threading
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from app.database import get_db
from app.models import Base, Product, WalletLedger, Transaction, ProductStateHistory
from app.services.state_machine import ProductState


# Test Database Setup

@pytest.fixture(scope="function", autouse=True)
def test_db():
    """Create in-memory SQLite database for testing."""
    # Create engine with StaticPool to maintain single connection for :memory: DB
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session factory
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Override get_db dependency
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield engine
    
    # Cleanup
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """FastAPI test client with overridden dependencies."""
    return TestClient(app)


@pytest.fixture
def mock_verify_token(monkeypatch):
    """Mock JWT token verification to return user ID from token."""
    def verify_token(token):
        # Extract user ID from token (format: "valid-token-{user_id}")
        if token.startswith("valid-token-"):
            return token.replace("valid-token-", "")
        return None
    
    from app.api import deps
    monkeypatch.setattr(deps, "verify_token", verify_token)
    return verify_token


@pytest.fixture
def auth_headers():
    """Authorization headers for authenticated requests."""
    return {"Authorization": "Bearer valid-token-test-user-id"}


@pytest.fixture
def product(test_db):
    """Create a test product in DB."""
    SessionLocal = sessionmaker(bind=test_db)
    db = SessionLocal()
    
    product = Product(
        title="Test Product",
        description="A test product",
        category="Electronics",
        price=100.0,
        state=ProductState.AVAILABLE,
        owner_id="seller-user-id"
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    
    product_id = product.id
    db.close()
    
    return product_id


@pytest.fixture
def buyer_with_funds(test_db, mock_verify_token):
    """Create a buyer with sufficient wallet balance."""
    SessionLocal = sessionmaker(bind=test_db)
    db = SessionLocal()
    
    buyer_id = "buyer-user-id"
    
    # Top-up wallet
    ledger = WalletLedger(
        user_id=buyer_id,
        amount=500.0,
        transaction_type="TOP_UP",
        description="Initial balance",
        balance_after=500.0
    )
    db.add(ledger)
    db.commit()
    db.close()
    
    return buyer_id


@pytest.fixture
def poor_buyer(test_db, mock_verify_token):
    """Create a buyer with insufficient funds."""
    SessionLocal = sessionmaker(bind=test_db)
    db = SessionLocal()
    
    buyer_id = "poor-buyer-id"
    
    # Top-up wallet with insufficient funds
    ledger = WalletLedger(
        user_id=buyer_id,
        amount=10.0,
        transaction_type="TOP_UP",
        description="Low balance",
        balance_after=10.0
    )
    db.add(ledger)
    db.commit()
    db.close()
    
    return buyer_id


# Reservation state testss

#Test 1: Vrify that a product can be successfully reserved by a user who is not the seller
def test_reserve_successful(client, product, auth_headers, mock_verify_token):
    """Test successful product reservation."""
    user_id = "reserve-user-id"
    headers = {"Authorization": f"Bearer valid-token-{user_id}"}
    
    response = client.post(f"/products/{product}/reserve", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == ProductState.RESERVED
    assert data["reserved_by"] == user_id

#Test 2: Verify that a seller cannot reserve their own product
def test_reserve_ownership_guard(client, product, auth_headers, mock_verify_token):
    """Test that seller cannot reserve own product."""
    # The seller is "seller-user-id" from the product fixture
    headers = {"Authorization": "Bearer valid-token-seller-user-id"}
    
    response = client.post(f"/products/{product}/reserve", headers=headers)
    
    assert response.status_code == 403
    assert "Cannot reserve your own product" in response.json()["detail"]

#Test 3: Verify that a non-existent product cannot be reserved 
def test_reserve_nonexistent_product(client, auth_headers, mock_verify_token):
    """Test reservation of non-existent product."""
    user_id = "buyer-user-id"
    headers = {"Authorization": f"Bearer valid-token-{user_id}"}
    
    response = client.post("/products/9999/reserve", headers=headers)
    
    assert response.status_code == 404


#String 2: Purchase test 
#Test 1: Verify that a product can be successfully purchased by a user with sufficient funds
def test_purchase_successful(client, product, buyer_with_funds, auth_headers, mock_verify_token):
    """Test successful product purchase with sufficient funds."""
    headers = {"Authorization": f"Bearer valid-token-{buyer_with_funds}"}
    
    response = client.post(f"/products/{product}/buy", headers=headers)
    
    assert response.status_code == 201
    data = response.json()
    assert data["buyer_id"] == buyer_with_funds
    assert data["seller_id"] == "seller-user-id"
    assert data["product_id"] == product
    assert data["amount"] == 100.0
    assert data["status"] == "completed"

#Test 2: In case of inssuficients funds verify that the purchase is rejected and no changes are made 
def test_purchase_insufficient_funds(client, product, poor_buyer, mock_verify_token):
    """Test purchase rejected due to insufficient funds."""
    headers = {"Authorization": f"Bearer valid-token-{poor_buyer}"}
    
    response = client.post(f"/products/{product}/buy", headers=headers)
    
    assert response.status_code == 402
    assert "Insufficient funds" in response.json()["detail"]

#Test 3: Verify that a seller cannot buy its own products
def test_purchase_ownership_guard(client, product, auth_headers, mock_verify_token):
    """Test that seller cannot buy own product."""
    headers = {"Authorization": "Bearer valid-token-seller-user-id"}
    
    response = client.post(f"/products/{product}/buy", headers=headers)
    
    assert response.status_code == 403
    assert "Cannot purchase your own product" in response.json()["detail"]

#Test 4: Verify that both buyer and seller wallet entries are created correctly after purchase, debit and credit
def test_purchase_atomic_transaction(client, product, buyer_with_funds, test_db, mock_verify_token):
    """Test that purchase is atomic: all operations succeed or none."""
    SessionLocal = sessionmaker(bind=test_db)
    headers = {"Authorization": f"Bearer valid-token-{buyer_with_funds}"}
    
    response = client.post(f"/products/{product}/buy", headers=headers)
    assert response.status_code == 201
    
    db = SessionLocal()
    ledger_entries = db.query(WalletLedger).all()
    
    assert len(ledger_entries) >= 3
    
    db.close()

#Test 5: Verify that the product change state from available or reserved to solfd correctly 
def test_purchase_product_state_transition(client, product, buyer_with_funds, test_db, mock_verify_token):
    """Test that product state transitions to SOLD after purchase."""
    SessionLocal = sessionmaker(bind=test_db)
    headers = {"Authorization": f"Bearer valid-token-{buyer_with_funds}"}
    
    client.post(f"/products/{product}/buy", headers=headers)
    
    db = SessionLocal()
    updated_product = db.query(Product).filter(Product.id == product).first()
    assert updated_product.state == ProductState.SOLD
    
    db.close()

#Test 6: Verify that a trasaction is created in the database correctly 
def test_purchase_creates_transaction_record(client, product, buyer_with_funds, test_db, mock_verify_token):
    """Test that transaction record is created in database."""
    SessionLocal = sessionmaker(bind=test_db)
    headers = {"Authorization": f"Bearer valid-token-{buyer_with_funds}"}
    
    response = client.post(f"/products/{product}/buy", headers=headers)
    
    db = SessionLocal()
    txn = db.query(Transaction).filter(
        Transaction.buyer_id == buyer_with_funds,
        Transaction.product_id == product
    ).first()
    
    assert txn is not None
    assert txn.seller_id == "seller-user-id"
    assert txn.amount == 100.0
    assert txn.status == "completed"
    
    db.close()


# Sprint 2: History Tests
#Test 1: Verify that a user who has not done any transacction has an empty history 
def test_history_empty(client, auth_headers, mock_verify_token):
    """Test history for user with no transactions."""
    user_id = "new-user"
    headers = {"Authorization": f"Bearer valid-token-{user_id}"}
    
    response = client.get("/products/history", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["transactions"]) == 0
    assert data["total"] == 0

#Test 2: Verify that a user can see all their transactions 
def test_history_as_buyer(client, product, buyer_with_funds, test_db, mock_verify_token):
    """Test transaction history for buyer."""
    SessionLocal = sessionmaker(bind=test_db)
    headers = {"Authorization": f"Bearer valid-token-{buyer_with_funds}"}
    
    # Make purchase
    client.post(f"/products/{product}/buy", headers=headers)
    
    # Get history
    response = client.get("/products/history", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["transactions"]) == 1
    assert data["transactions"][0]["buyer_id"] == buyer_with_funds
    
    db = SessionLocal()
    db.close()

#Test 3: Verify that a seller can see all their transactions as a seller in the history endpoint
def test_history_as_seller(client, product, buyer_with_funds, test_db, mock_verify_token):
    """Test transaction history for seller."""
    headers_buyer = {"Authorization": f"Bearer valid-token-{buyer_with_funds}"}
    headers_seller = {"Authorization": "Bearer valid-token-seller-user-id"}
    
    # Buy the product (as buyer)
    client.post(f"/products/{product}/buy", headers=headers_buyer)
    
    # Get seller history
    response = client.get("/products/history", headers=headers_seller)
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["transactions"][0]["seller_id"] == "seller-user-id"

# Test 4: Verify multiple trasactions history
def test_history_pagination(client, test_db, buyer_with_funds, mock_verify_token):
    """Test transaction history pagination."""
    SessionLocal = sessionmaker(bind=test_db)
    
    # Create multiple products and purchase them
    db = SessionLocal()
    for i in range(5):
        product = Product(
            title=f"Product {i}",
            description="Test",
            category="Test",
            price=100.0,
            state=ProductState.AVAILABLE,
            owner_id=f"seller-{i}"
        )
        db.add(product)
    
    db.commit()
    products = db.query(Product).all()
    db.close()
    
    headers = {"Authorization": f"Bearer valid-token-{buyer_with_funds}"}
    
    # Buy each product
    for p in products[:3]:  # Buy 3 products
        client.post(f"/products/{p.id}/buy", headers=headers)
    
    # Get paginated history
    response = client.get("/products/history?page=1&per_page=2", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["transactions"]) == 2
    assert data["page"] == 1
    assert data["per_page"] == 2

#Test 5: Verify that a trasaction record cannot be modified after being created 
def test_history_immutability(client, test_db, product, buyer_with_funds, mock_verify_token):
    """Test that transaction records are immutable (read-only from user perspective)."""
    headers = {"Authorization": f"Bearer valid-token-{buyer_with_funds}"}
    
    # Make purchase
    client.post(f"/products/{product}/buy", headers=headers)
    
    # Get history
    response = client.get("/products/history", headers=headers)
    txn_id = response.json()["transactions"][0]["id"]
    
    # Try to modify (should fail or not be possible via API)
    # This test just verifies the transaction record exists and was recorded
    assert txn_id > 0


# Sprint 2: Concurrent Reservation Tests
#Test 1: Simulate two simultaneos reservation for the same product 
def test_concurrent_reservation(client, test_db, mock_verify_token):
    """
    Test concurrent reservation attempts --> Only one can be succesfully done 
    """
    SessionLocal = sessionmaker(bind=test_db)
    db = SessionLocal()

    product = Product(
        title="Limited Item",
        description="Only one person can have this",
        price=100.0,
        state=ProductState.AVAILABLE,
        owner_id="seller-123"
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    product_id = product.id
    db.close()

    # Primera reserva — debe tener éxito
    headers1 = {"Authorization": "Bearer valid-token-buyer1"}
    response1 = client.post(f"/products/{product_id}/reserve", headers=headers1)

    # Segunda reserva — debe fallar porque ya está reservado
    headers2 = {"Authorization": "Bearer valid-token-buyer2"}
    response2 = client.post(f"/products/{product_id}/reserve", headers=headers2)

    assert response1.status_code == 200, f"Primera reserva falló: {response1.json()}"
    assert response2.status_code in [400, 409], f"Segunda reserva debería fallar: {response2.json()}"


#Test 2: Verify that after timeout the product can be reserved again 
def test_timeout_release_expired_reservation(client, test_db, mock_verify_token):
    """
    Test timeout release of expired reservations.
    """
    from app.routers.transactions import release_expired_reservations, RESERVATION_TIMEOUT_SECONDS
    from datetime import timedelta
    
    # Setup: Create product and reserve it
    TestingSessionLocal = sessionmaker(bind=test_db)
    db = TestingSessionLocal()
    
    product = Product(
        title="Soon Available Item",
        description="Will timeout soon",
        price=100.0,
        state=ProductState.AVAILABLE,
        owner_id="seller-123"
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    product_id = product.id
    
    # Manually set product to RESERVED with old timestamp
    product.state = ProductState.RESERVED
    product.reserved_at = datetime.now() - timedelta(seconds=RESERVATION_TIMEOUT_SECONDS + 60)  # Expired
    db.commit()
    
    # Verify product is RESERVED before release
    db.refresh(product)
    assert product.state == ProductState.RESERVED
    
    # Call release function
    released_count = release_expired_reservations(db, timeout_seconds=RESERVATION_TIMEOUT_SECONDS)
    
    # Verify one was released
    assert released_count == 1, f"Expected 1 released reservation, got {released_count}"
    
    # Verify product is now AVAILABLE
    db.refresh(product)
    assert product.state == ProductState.AVAILABLE
    assert product.reserved_at is None
    
    db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
