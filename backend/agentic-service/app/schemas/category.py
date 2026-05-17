from pydantic import BaseModel, Field, field_validator


class CategoryRequest(BaseModel):
    """Product data sent by the seller to request a category suggestion."""

    title: str = Field(
        ...,
        description="Product title as written by the seller.",
        examples=["iPhone 13 Pro 128GB"],
    )
    description: str = Field(
        ...,
        description="Product description as written by the seller.",
        examples=["Used for one year, minor screen scratches, battery at 87%."],
    )
    available_categories: list[str] = Field(
        ...,
        min_length=1,
        description=(
            "Non-empty list of category names the agent must choose from. "
            "The agent copies the chosen name exactly; it only proposes a new name "
            "when none of the provided options is a good fit."
        ),
        examples=[["Electronics", "Clothing & Accessories", "Home & Garden", "Other"]],
    )


class CategorySuggestion(BaseModel):
    """Category classification returned by the Wallabot agent."""

    suggested_category: str = Field(
        ...,
        description=(
            "Chosen category name. Either an exact copy of one entry from "
            "`available_categories` or a new name proposed by the agent when no "
            "existing category fits."
        ),
        examples=["Electronics"],
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Calibrated confidence score in [0.0, 1.0]. "
            "Higher values indicate the agent is more certain of the classification. "
            "A value of 0.0 is used for provider-failure fallback responses."
        ),
        examples=[0.92],
    )
    is_new_category: bool = Field(
        ...,
        description=(
            "True when the agent proposed a category name that is not present in "
            "`available_categories`. False when an existing category was selected."
        ),
        examples=[False],
    )

    @field_validator("suggested_category")
    @classmethod
    def category_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("suggested_category cannot be empty")
        return value.strip()
