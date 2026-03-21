import pytest
from pydantic import ValidationError

from app.schemas import CategorySuggestion


def test_category_suggestion_valid_data() -> None:
    suggestion = CategorySuggestion(suggested_category="Electronics", confidence=0.92)

    assert suggestion.suggested_category == "Electronics"
    assert suggestion.confidence == 0.92


def test_category_suggestion_rejects_empty_category() -> None:
    with pytest.raises(ValidationError):
        CategorySuggestion(suggested_category="", confidence=0.5)


def test_category_suggestion_rejects_confidence_out_of_range() -> None:
    with pytest.raises(ValidationError):
        CategorySuggestion(suggested_category="Electronics", confidence=1.5)
