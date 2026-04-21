import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./transactions.db")
    SECRET_KEY: str   = "mi_clave_secreta"  # must be the same as in auth-service 
    ALGORITHM: str    = "HS256"

    class Config:
        env_file = ".env"


settings = Settings()