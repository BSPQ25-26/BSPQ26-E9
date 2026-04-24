from fastapi import FastAPI
from app.api.v1.auth_router import router as auth_router
from app.api.v1.social_auth_router import router as social_auth_router
from app.db.init_db import init_db

app = FastAPI()


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(social_auth_router)