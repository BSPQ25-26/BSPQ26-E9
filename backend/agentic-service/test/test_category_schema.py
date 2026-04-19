import pytest
from pydantic import ValidationError

from app.schemas import CategoryRequest, CategorySuggestion, PriceRecommendation


def test_category_suggestion_valid_data() -> None:
    suggestion = CategorySuggestion(
        suggested_category="Electronics",
        confidence=0.92,
        is_new_category=False,
    )

    assert suggestion.suggested_category == "Electronics"
    assert suggestion.confidence == 0.92


def test_category_suggestion_rejects_empty_category() -> None:
    with pytest.raises(ValidationError):
        CategorySuggestion(suggested_category="", confidence=0.5, is_new_category=False)


def test_category_suggestion_rejects_confidence_out_of_range() -> None:
    with pytest.raises(ValidationError):
        CategorySuggestion(
            suggested_category="Electronics",
            confidence=1.5,
            is_new_category=False,
        )


def test_category_request_valid_data() -> None:
    request = CategoryRequest(
        title="iPhone 13",
        description="Used smartphone, 128GB",
        available_categories=["Electronics", "Other"],
    )

    assert request.title == "iPhone 13"
    assert request.available_categories == ["Electronics", "Other"]


def test_category_request_rejects_empty_available_categories() -> None:
    with pytest.raises(ValidationError):
        CategoryRequest(
            title="iPhone 13",
            description="Used smartphone, 128GB",
            available_categories=[],
        )


def test_price_recommendation_valid_data() -> None:
    recommendation = PriceRecommendation(
        recommended_price=129.99,
        price_range_min=110.0,
        price_range_max=150.0,
        data_source="Tavily web search",
    )

    assert recommendation.recommended_price == 129.99
    assert recommendation.price_range_min == 110.0
    assert recommendation.price_range_max == 150.0


def test_price_recommendation_rejects_negative_price() -> None:
    with pytest.raises(ValidationError):
        PriceRecommendation(
            recommended_price=-1.0,
            price_range_min=110.0,
            price_range_max=150.0,
            data_source="Tavily web search",
        )


def test_price_recommendation_rejects_max_not_greater_than_min() -> None:
    with pytest.raises(ValidationError):
        PriceRecommendation(
            recommended_price=129.99,
            price_range_min=150.0,
            price_range_max=140.0,
            data_source="Tavily web search",
        )
