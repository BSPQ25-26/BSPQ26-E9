from fastapi import APIRouter, HTTPException
from langchain_core.exceptions import OutputParserException
from pydantic import ValidationError

from app.agent.category_agent import suggest_category
from app.schemas.category import CategoryRequest, CategorySuggestion
from app.schemas.price import PriceRequest

router = APIRouter(prefix="/wallabot", tags=["wallabot"])


@router.post("/category", response_model=CategorySuggestion)
async def category_suggestion(req: CategoryRequest) -> CategorySuggestion:
    try:
        return suggest_category(req)
    except (OutputParserException, ValidationError) as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "agent_validation_failure", "message": str(exc)},
        ) from exc


@router.post("/price")
async def price_recommendation(req: PriceRequest) -> dict[str, str]:
    raise HTTPException(status_code=501, detail="Not Implemented")
