# ruff: noqa: E402
import os
import sys

service_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if service_root in sys.path:
    sys.path.remove(service_root)
sys.path.insert(0, service_root)

for module_name in list(sys.modules):
    if module_name == "app" or module_name.startswith("app."):
        del sys.modules[module_name]

import pytest  # noqa: E402
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    os.getenv("DATABASE_URL", "sqlite:///./test_inventory.db"),
)

engine_kwargs = {}
if TEST_DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(TEST_DATABASE_URL, **engine_kwargs)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def _load_service_modules():
    if service_root in sys.path:
        sys.path.remove(service_root)
    sys.path.insert(0, service_root)

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]

    from app.db.base import Base
    from app.db.session import get_db
    from app.main import app

    return app, Base, get_db


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def make_access_token(subject: str) -> str:
    if service_root in sys.path:
        sys.path.remove(service_root)
    sys.path.insert(0, service_root)

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]

    from app.auth import ALGORITHM, SECRET_KEY

    return jwt.encode({"sub": subject}, SECRET_KEY, algorithm=ALGORITHM)


@pytest.fixture()
def client():
    app, Base, get_db = _load_service_modules()

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    from app.db.base import Base
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def seller_token():
    return make_access_token("seller@example.com")


@pytest.fixture()
def other_seller_token():
    return make_access_token("other-seller@example.com")


@pytest.fixture()
def auth_headers(seller_token):
    return {"Authorization": f"Bearer {seller_token}"}
