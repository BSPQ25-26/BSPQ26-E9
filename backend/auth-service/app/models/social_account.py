import os
from sqlalchemy import Column, String, DateTime, BigInteger, ForeignKey, UniqueConstraint
from datetime import datetime
from app.db.base import Base

DB_SCHEMA = os.getenv("DB_SCHEMA", None)


class SocialAccount(Base):
    __tablename__ = "social_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_social_provider"),
        {"schema": DB_SCHEMA} if DB_SCHEMA else {},
    )

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey(
        f"{DB_SCHEMA}.users.id" if DB_SCHEMA else "users.id",
        ondelete="CASCADE"
    ), nullable=False)
    provider = Column(String(20), nullable=False)
    provider_user_id = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)