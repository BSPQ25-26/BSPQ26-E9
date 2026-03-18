import os

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.core.security import hash_password
from app.models.user import User


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def seed_sample_users():
    should_seed = _as_bool(os.getenv("AUTH_SEED_SAMPLE_DATA", "false"))
    if not should_seed:
        return

    sample_users = [
        {
            "email": "alice@example.com",
            "password": "alice123",
            "wallet_balance": 120.0,
            "avg_rating": 4.8,
        },
        {
            "email": "bob@example.com",
            "password": "bob123",
            "wallet_balance": 80.5,
            "avg_rating": 4.2,
        },
        {
            "email": "charlie@example.com",
            "password": "charlie123",
            "wallet_balance": 45.0,
            "avg_rating": 3.9,
        },
    ]

    db = SessionLocal()
    try:
        for sample in sample_users:
            existing_user = db.query(User).filter(User.email == sample["email"]).first()
            if existing_user:
                continue

            db.add(
                User(
                    email=sample["email"],
                    password_hash=hash_password(sample["password"]),
                    wallet_balance=sample["wallet_balance"],
                    avg_rating=sample["avg_rating"],
                )
            )

        db.commit()
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    seed_sample_users()