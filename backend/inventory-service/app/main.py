from contextlib import asynccontextmanager
import os
import shutil

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.v1.product_router import UPLOAD_DIR, router as product_router
from app.db.init_db import init_db

LEGACY_UPLOAD_DIR = "uploads"


def prepare_upload_storage():
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    if os.path.abspath(UPLOAD_DIR) == os.path.abspath(LEGACY_UPLOAD_DIR):
        return

    if not os.path.isdir(LEGACY_UPLOAD_DIR):
        return

    for filename in os.listdir(LEGACY_UPLOAD_DIR):
        legacy_path = os.path.join(LEGACY_UPLOAD_DIR, filename)
        target_path = os.path.join(UPLOAD_DIR, filename)

        if os.path.isfile(legacy_path) and not os.path.exists(target_path):
            shutil.copy2(legacy_path, target_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    prepare_upload_storage()
    yield

prepare_upload_storage()

app = FastAPI(lifespan=lifespan)

app.include_router(product_router, prefix="/api/v1")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Healthcheck endpoint igual que en auth-service
@app.get("/health")
def health():
    return {"status": "ok"}
