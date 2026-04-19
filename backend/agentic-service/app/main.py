from fastapi import FastAPI

from app.api import wallabot_router

app = FastAPI(title="Wallabot Agentic Service")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(wallabot_router)
