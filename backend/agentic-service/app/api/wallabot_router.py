import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from langchain_core.exceptions import OutputParserException
from pydantic import ValidationError

from app.agent.category_agent import suggest_category
from app.schemas.category import CategoryRequest, CategorySuggestion
from app.schemas.price import PriceRequest

router = APIRouter(prefix="/wallabot", tags=["wallabot"])
logger = logging.getLogger(__name__)


@router.post("/category", response_model=CategorySuggestion)
async def category_suggestion(req: CategoryRequest) -> CategorySuggestion:
    try:
        return await run_in_threadpool(suggest_category, req)
    except (OutputParserException, ValidationError) as exc:
        logger.exception(
            "Category suggestion failed due to agent output validation title=%r error_type=%s",
            req.title,
            exc.__class__.__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "agent_validation_failure",
                "message": "Failed to process agent output.",
            },
        ) from exc


@router.post("/price", responses={501: {"description": "Not Implemented"}})
async def price_recommendation(req: PriceRequest) -> None:
    raise HTTPException(status_code=501, detail="Not Implemented")
