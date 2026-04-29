import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from langchain_core.exceptions import OutputParserException
from pydantic import ValidationError

from app.agent.category_agent import suggest_category
from app.agent.price_agent import recommend_price
from app.schemas.category import CategoryRequest, CategorySuggestion
from app.schemas.price import PriceRecommendation, PriceRequest

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
                "message": "The request could not be processed due to an internal validation failure.",
            },
        ) from exc


@router.post("/price", response_model=PriceRecommendation)
async def price_recommendation(req: PriceRequest) -> PriceRecommendation:
    try:
        return await run_in_threadpool(recommend_price, req)
    except (OutputParserException, ValidationError) as exc:
        logger.exception(
            "Price recommendation failed due to agent output validation title=%r error_type=%s",
            req.title,
            exc.__class__.__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "agent_validation_failure",
                "message": "The request could not be processed due to an internal validation failure.",
            },
        ) from exc
    except Exception as exc:
        logger.exception(
            "Price recommendation failed due to provider error title=%r error_type=%s",
            req.title,
            exc.__class__.__name__,
        )
        raise HTTPException(
            status_code=502,
            detail={
                "error": "agent_provider_failure",
                "message": "Wallabot could not reach the pricing provider.",
            },
        ) from exc
