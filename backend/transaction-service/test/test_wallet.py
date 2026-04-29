"""
Unit tests for Wallet endpoints.

Tests:
1. Top-up: successful top-up, validation of positive amounts, balance update
2. Balance: correct balance retrieval, empty wallet default to 0
3. History: pagination, correct entries, reverse chronological order
4. Balance Integrity: consistency across ledger entries
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models import Base, WalletLedger


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
    """FastAPI test client with database ready."""
    return TestClient(app)


@pytest.fixture
def mock_user_id():
    """Mock authenticated user ID."""
    return "test-user-123"


@pytest.fixture
def auth_headers(mock_user_id, monkeypatch):
    """Authorization headers for authenticated requests."""
    def mock_verify_token(token):
        if token == "valid-token":
            return mock_user_id
        return None
    
    from app.api import deps
    monkeypatch.setattr(deps, "verify_token", mock_verify_token)
    
    return {"Authorization": "Bearer valid-token"}


# Sprint 2: Top-Up Tests 
#Test 1: Succesful recharge of the wallet 
def test_topup_successful(client, auth_headers, test_db, mock_user_id):
    """Test successful wallet top-up."""
    response = client.post(
        "/wallet/topup",
        json={"amount": 100.0},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == mock_user_id
    assert data["balance"] == 100.0
    assert "last_update" in data

#Test 2: Verify that mutiple top-ups accumulate correctly 
def test_topup_multiple(client, auth_headers, test_db, mock_user_id):
    """Test multiple top-ups accumulate correctly."""
    # First top-up
    response1 = client.post(
        "/wallet/topup",
        json={"amount": 50.0},
        headers=auth_headers
    )
    assert response1.json()["balance"] == 50.0
    
    # Second top-up
    response2 = client.post(
        "/wallet/topup",
        json={"amount": 30.0},
        headers=auth_headers
    )
    assert response2.json()["balance"] == 80.0

#Test 3: Negative amounts are rejected
def test_topup_negative_amount(client, auth_headers):
    """Test that negative amounts are rejected."""
    response = client.post(
        "/wallet/topup",
        json={"amount": -50.0},
        headers=auth_headers
    )
    # Should fail validation
    assert response.status_code == 422

#Test 4: Zero amount is rejected
def test_topup_zero_amount(client, auth_headers):
    """Test that zero amount is rejected."""
    response = client.post(
        "/wallet/topup",
        json={"amount": 0.0},
        headers=auth_headers
    )
    # Should fail validation
    assert response.status_code == 422


# Sprint 2: Balance Tests 

#Test 1: A new users balance is 0 by default 
def test_balance_empty_wallet(client, auth_headers, mock_user_id):
    """Test balance for user with no history defaults to 0."""
    response = client.get("/wallet/balance", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == mock_user_id
    assert data["balance"] == 0.0

#Test 2: Balnce reflects top-up correctly
def test_balance_after_topup(client, auth_headers, mock_user_id):
    """Test balance reflects top-up correctly."""
    # Top-up first
    client.post("/wallet/topup", json={"amount": 100.0}, headers=auth_headers)
    
    # Check balance
    response = client.get("/wallet/balance", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["balance"] == 100.0
    assert data["user_id"] == mock_user_id

#Test 3: Multiple balance checks return the same value
def test_balance_consistency(client, auth_headers):
    """Test that multiple balance checks return same value."""
    client.post("/wallet/topup", json={"amount": 75.0}, headers=auth_headers)
    
    response1 = client.get("/wallet/balance", headers=auth_headers)
    response2 = client.get("/wallet/balance", headers=auth_headers)
    
    assert response1.json()["balance"] == response2.json()["balance"]


# Sprint 2: History Tests 

#Test 1: History is empty for users without movements  
def test_history_empty_wallet(client, auth_headers, mock_user_id):
    """Test history for user with no entries."""
    response = client.get("/wallet/history", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == mock_user_id
    assert data["balance"] == 0.0
    assert len(data["entries"]) == 0
    assert data["total"] == 0

#Test 2: Shows all ledger entries for a user
def test_history_with_entries(client, auth_headers, mock_user_id):
    """Test history lists all ledger entries."""
    # Create two top-ups
    client.post("/wallet/topup", json={"amount": 50.0}, headers=auth_headers)
    client.post("/wallet/topup", json={"amount": 30.0}, headers=auth_headers)
    
    response = client.get("/wallet/history", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["entries"]) == 2
    assert data["balance"] == 80.0

#Test 3: Pagination works correctly
def test_history_pagination(client, auth_headers):
    """Test history pagination."""
    # Create 5 top-ups
    for amount in [10.0, 20.0, 30.0, 40.0, 50.0]:
        client.post("/wallet/topup", json={"amount": amount}, headers=auth_headers)
    
    # Page 1 with 3 items
    response1 = client.get("/wallet/history?page=1&per_page=3", headers=auth_headers)
    data1 = response1.json()
    assert data1["page"] == 1
    assert data1["per_page"] == 3
    assert len(data1["entries"]) == 3
    assert data1["total"] == 5
    
    # Page 2 with 3 items
    response2 = client.get("/wallet/history?page=2&per_page=3", headers=auth_headers)
    data2 = response2.json()
    assert data2["page"] == 2
    assert len(data2["entries"]) == 2

#Test 4: New entries appears at the top 
def test_history_reverse_chronological(client, auth_headers):
    """Test that history entries are in reverse chronological order."""
    # Create multiple entries
    client.post("/wallet/topup", json={"amount": 10.0}, headers=auth_headers)
    client.post("/wallet/topup", json={"amount": 20.0}, headers=auth_headers)
    client.post("/wallet/topup", json={"amount": 30.0}, headers=auth_headers)
    
    response = client.get("/wallet/history", headers=auth_headers)
    entries = response.json()["entries"]
    
    # Check that entries are in reverse order (newest first)
    for i in range(len(entries) - 1):
        assert entries[i]["created_at"] >= entries[i + 1]["created_at"]


#Sprint 2: Balance Integrity Tests
#Test 1: Verify that the balance is consistent after multiple operations
def test_balance_integrity_after_multiple_ops(client, auth_headers):
    """Test that balance stays consistent across multiple operations."""
    operations = [10.0, 25.0, 15.0, 50.0]
    expected_balance = 0.0
    
    for amount in operations:
        client.post("/wallet/topup", json={"amount": amount}, headers=auth_headers)
        expected_balance += amount
    
    response = client.get("/wallet/balance", headers=auth_headers)
    assert response.json()["balance"] == expected_balance

#Test 2: Verify that balance_after in BD is the same as the reported balance from the API
def test_balance_after_topup_matches_ledger(client, auth_headers, test_db):
    """Test that balance_after in ledger matches reported balance."""
    response = client.post(
        "/wallet/topup",
        json={"amount": 100.0},
        headers={"Authorization": "Bearer valid-token"}
    )
    
    balance_response = response.json()["balance"]
    
    # Get ledger entry directly
    SessionLocal = sessionmaker(bind=test_db)
    db = SessionLocal()
    latest_entry = db.query(WalletLedger).order_by(WalletLedger.id.desc()).first()
    
    assert float(latest_entry.balance_after) == balance_response
    db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
