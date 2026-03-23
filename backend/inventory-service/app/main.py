from fastapi import FastAPI
from app.api.v1.product_router import router as product_router
from app.db.init_db import init_db

app = FastAPI()

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(product_router, prefix="/api/v1")

# Healthcheck endpoint igual que en auth-service
@app.get("/health")
def health():
    return {"status": "ok"}
