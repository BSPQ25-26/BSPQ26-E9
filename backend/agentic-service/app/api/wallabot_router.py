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

_422 = {
    "description": "Request body failed validation.",
    "content": {
        "application/json": {
            "example": {
                "detail": [
                    {
                        "loc": ["body", "available_categories"],
                        "msg": "List should have at least 1 item after validation, not 0",
                        "type": "too_short",
                    }
                ]
            }
        }
    },
}

_500 = {
    "description": (
        "The LLM produced output that did not conform to the expected schema after "
        "3 retries. Retrying the request may succeed."
    ),
    "content": {
        "application/json": {
            "example": {
                "detail": {
                    "error": "agent_validation_failure",
                    "message": "The request could not be processed due to an internal validation failure.",
                }
            }
        }
    },
}

_502 = {
    "description": "The upstream LLM or search provider was unreachable.",
    "content": {
        "application/json": {
            "example": {
                "detail": {
                    "error": "agent_provider_failure",
                    "message": "Wallabot could not reach the pricing provider.",
                }
            }
        }
    },
}


@router.post(
    "/category",
    response_model=CategorySuggestion,
    summary="Suggest a product category",
    description=(
        "Classifies a product into one of the caller-provided categories using a "
        "LangChain LCEL chain backed by GPT-4o-mini.\n\n"
        "The agent prefers existing categories; it proposes a new one only when none "
        "of the provided options is a good fit, setting `is_new_category=true`.\n\n"
        "On validation failure the agent retries up to **3 times** with progressively "
        "detailed feedback. On LLM provider failure it returns the closest available "
        "category with `confidence=0.0` rather than raising an error."
    ),
    response_description="Category suggestion with confidence score.",
    responses={422: _422, 500: _500},
)
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


@router.post(
    "/price",
    response_model=PriceRecommendation,
    summary="Get a price recommendation",
    description=(
        "Estimates a fair second-hand selling price in EUR for the described product.\n\n"
        "The agent first queries **Tavily** for live market listings, then passes the "
        "results to GPT-4o-mini to produce a structured price range adjusted for the "
        "declared condition.\n\n"
        "When Tavily returns no results the endpoint still returns **HTTP 200** with "
        "`data_source='fallback: no market data found'` and a conservative LLM-based "
        "estimate — it never returns a 5xx error solely because of missing market data.\n\n"
        "On LLM provider failure a hardcoded condition-scaled fallback is returned so "
        "the seller always receives a usable response."
    ),
    response_description=(
        "Price recommendation with a recommended price, min/max range, and the source "
        "of the market data used."
    ),
    responses={422: _422, 500: _500, 502: _502},
)
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
