"""
Application settings loaded from environment variables.
"""
import os
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
    
    model_config = ConfigDict(
        env_file=Path(__file__).parent.parent.parent.parent.parent / ".env",
        extra="ignore"
    )


settings = Settings()

# Use Supabase if available, otherwise fallback to SQLite
if settings.TRANSACTION_DATABASE_URL:
    settings.DATABASE_URL = settings.TRANSACTION_DATABASE_URL
    # print(f"✓ Using Supabase: {settings.DATABASE_URL[:50]}...")
else:
    # print(f"⚠ Using SQLite fallback: {settings.DATABASE_URL}")
    pass