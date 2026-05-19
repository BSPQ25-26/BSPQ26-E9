import os
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from datetime import datetime
from app.db.base import Base

DATABASE_URL = os.getenv("AUTH_DATABASE_URL", "sqlite:///./auth.db")
DB_SCHEMA = None if DATABASE_URL.startswith("sqlite") else os.getenv("DB_SCHEMA", None)


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("from_user_id", "transaction_id", name="uq_rating_user_transaction"),
        {"schema": DB_SCHEMA} if DB_SCHEMA else {},
    )

    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, nullable=False)
    to_user_id = Column(Integer, nullable=False, index=True)
    transaction_id = Column(Integer, nullable=False)
    stars = Column(Integer, nullable=False)
    review_text = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
