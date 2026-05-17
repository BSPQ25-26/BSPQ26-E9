"""
Application settings loaded from environment variables.
"""
#import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str             = "sqlite:///./transactions.db"
    TRANSACTION_DATABASE_URL: str = ""
    SECRET_KEY: str               = "mi_clave_secreta"
    ALGORITHM: str                = "HS256"
    #SPRINT 3: Reservation Timeout Tuning
    RESERVATION_TIMEOUT_SECONDS: int = 900
    # Background thread: how often to scan for expired reservations (seconds)
    RESERVATION_CLEANUP_INTERVAL_SECONDS: int = 60
    # Set true in Docker/production; keep false in tests to avoid extra DB sessions
    RESERVATION_CLEANUP_ENABLED: bool = False

    model_config = ConfigDict(
        env_file=Path(__file__).parent.parent.parent.parent.parent / ".env",
        extra="ignore"
    )


settings = Settings()

# Use Supabase if available, otherwise fallback to SQLite
if settings.TRANSACTION_DATABASE_URL:
    settings.DATABASE_URL = settings.TRANSACTION_DATABASE_URL
    # debug: using Supabase (DATABASE_URL)
else:
    # debug: using SQLite fallback (DATABASE_URL)
    pass