import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./transactions.db"  # default local without Docker
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

#Sprint 3: Rollback on Failure and exception handling
def get_db():
    """
    Provides a databse session with automatic rollback on failure
    """
    db = SessionLocal()
    try:
        yield db
    except Exception: 
        db.rollback()
        raise
    finally:
        db.close()