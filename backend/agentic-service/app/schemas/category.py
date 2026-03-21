from pydantic import BaseModel, Field, field_validator

class CategorySuggestion(BaseModel):
    suggested_category: str = Field(
        ...,
        description="The most appropriate product category for the listing.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 (uncertain) and 1.0 (certain).",
    )

    @field_validator("suggested_category")
    @classmethod
    def category_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("suggested_category cannot be empty")
        return value.strip()
