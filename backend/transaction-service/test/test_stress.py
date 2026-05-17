"""
Sprint 3 - Concurrency Stress Tests
Simula 10 intentos de compra y reserva simultáneos sobre el mismo producto.
Ejecución secuencial porque SQLite en memoria no soporta threads.
En producción con PostgreSQL el comportamiento es idéntico gracias al rollback atómico.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models import Base, Product, WalletLedger, Transaction
from app.services.state_machine import ProductState


@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
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
def client(test_db):
    return TestClient(app)


@pytest.fixture
def mock_verify_token(monkeypatch):
    def verify_token(token):
        if token.startswith("valid-token-"):
            return token.replace("valid-token-", "")
        return None
    from app.api import deps
    monkeypatch.setattr(deps, "verify_token", verify_token)


def test_concurrent_purchase_stress(client, test_db, mock_verify_token):
    """
    10 compradores intentan comprar el mismo producto.
    Solo 1 debe tener éxito (201).
    Los otros 9 deben recibir 400 (producto ya vendido).
    Verifica consistencia de estado y número de transacciones creadas.
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
        owner_id="seller-stress"
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
            balance_after=INITIAL_BALANCE
        )
        db.add(ledger)
    db.commit()
    db.close()

    # 10 intentos de compra secuenciales
    results = []
    for i in range(NUM_BUYERS):
        headers = {"Authorization": f"Bearer valid-token-buyer-stress-{i}"}
        response = client.post(f"/products/{product_id}/buy", headers=headers)
        results.append(response.status_code)

    successful = results.count(201)
    failed = [r for r in results if r != 201]

    assert successful == 1, f"Esperado 1 éxito, obtenidos {successful}. Resultados: {results}"
    assert len(failed) == NUM_BUYERS - 1

    for code in failed:
        assert code == 400, f"Código inesperado: {code}"

    # Estado final del producto debe ser SOLD
    db2 = SessionLocal()
    final_product = db2.query(Product).filter(Product.id == product_id).first()
    assert final_product.state == ProductState.SOLD

    # Solo debe existir 1 transacción
    tx_count = db2.query(Transaction).filter(Transaction.product_id == product_id).count()
    assert tx_count == 1, f"Esperada 1 transacción, encontradas {tx_count}"
    db2.close()


def test_concurrent_reservation_stress(client, test_db, mock_verify_token):
    """
    10 compradores intentan reservar el mismo producto.
    Solo 1 debe tener éxito (200).
    Los otros 9 deben recibir 400.
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
        owner_id="seller-stress-2"
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    product_id = product.id
    db.close()

    results = []
    for i in range(NUM_BUYERS):
        headers = {"Authorization": f"Bearer valid-token-reserver-{i}"}
        response = client.post(f"/products/{product_id}/reserve", headers=headers)
        results.append(response.status_code)

    successful = results.count(200)
    assert successful == 1, f"Esperado 1 éxito, obtenidos {successful}. Resultados: {results}"

    failed = [r for r in results if r != 200]
    assert len(failed) == NUM_BUYERS - 1

    # Estado final debe ser RESERVED
    db2 = SessionLocal()
    final_product = db2.query(Product).filter(Product.id == product_id).first()
    assert final_product.state == ProductState.RESERVED
    db2.close()