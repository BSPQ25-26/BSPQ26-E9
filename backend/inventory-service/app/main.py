from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.v1.product_router import router as product_router
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

# Create directory for local image storage for tests
os.makedirs("uploads", exist_ok=True)

app = FastAPI(lifespan=lifespan)

app.include_router(product_router, prefix="/api/v1")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Healthcheck endpoint igual que en auth-service
@app.get("/health")
def health():
    return {"status": "ok"}
