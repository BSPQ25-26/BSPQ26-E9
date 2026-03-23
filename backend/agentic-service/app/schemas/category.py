from pydantic import BaseModel, Field, field_validator


class CategoryRequest(BaseModel):
    title: str
    description: str
    available_categories: list[str] = Field(
        ...,
        description="Category list provided by the caller (hardcoded in Sprint 1).",
    )


class CategorySuggestion(BaseModel):
    suggested_category: str = Field(
        ...,
        description="Exact name from available_categories, or a new proposed name.",
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    is_new_category: bool = Field(
        ...,
        description=(
            "True if the agent could not match any existing category and proposed a new one."
        ),
    )

    @field_validator("suggested_category")
    @classmethod
    def category_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("suggested_category cannot be empty")
        return value.strip()
