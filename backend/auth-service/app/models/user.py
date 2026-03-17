from sqlalchemy import Column, Integer, String, DateTime, Float
from datetime import datetime
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    wallet_balance = Column(Float, default=0.0)
    avg_rating = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)