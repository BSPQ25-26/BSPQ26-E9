from fastapi import FastAPI
from app.api.v1.product_router import router as product_router

app = FastAPI()

app.include_router(product_router, prefix="/api/v1")
