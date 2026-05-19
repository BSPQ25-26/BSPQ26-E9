import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import wallabot_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    from app.agent import tracing
    if tracing.is_tracing_enabled():
        logger.info(
            "Wallabot LangSmith tracing ENABLED project=%r",
            tracing.get_project_name(),
        )
    else:
        logger.warning(
            "Wallabot LangSmith tracing DISABLED — set LANGCHAIN_TRACING_V2=true or LANGSMITH_TRACING=true to enable"
        )
    yield


_DESCRIPTION = """
Wallabot is the AI subsystem of Mini-Wallapop, a C2C second-hand marketplace.

## Capabilities

* **Category suggestion** — classifies a product into a caller-provided taxonomy using
  GPT-4o-mini. Retries up to 3 times on malformed output and falls back gracefully on
  provider failure.
* **Price recommendation** — searches live market prices via Tavily and returns a
  structured EUR estimate adjusted for product condition.

## Behaviour

All endpoints are **stateless**: each request is fully self-contained with no session
memory between calls.

When LangSmith tracing is enabled (`LANGCHAIN_TRACING_V2=true`), every chain invocation
is automatically recorded under the configured project for monitoring and debugging.
"""

_TAGS_METADATA = [
    {
        "name": "wallabot",
        "description": (
            "AI-powered product intelligence. Uses LangChain LCEL chains backed by "
            "OpenAI GPT-4o-mini and Tavily web search."
        ),
    },
    {
        "name": "health",
        "description": "Service liveness probe.",
    },
]

app = FastAPI(
    title="Wallabot Agentic Service",
    description=_DESCRIPTION,
    version="1.0.0",
    openapi_tags=_TAGS_METADATA,
    lifespan=lifespan,
)

_frontend_url = os.getenv("FRONTEND_URL", "https://wallabot-frontend.onrender.com")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/health",
    tags=["health"],
    summary="Liveness check",
    response_description="Service is running",
)
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(wallabot_router)
