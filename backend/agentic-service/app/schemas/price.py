from pydantic import BaseModel, Field, field_validator


class PriceRequest(BaseModel):
    title: str
    description: str
    condition: str = Field(
        ...,
        description="Product condition: New, Like New, Good, Fair, or Poor.",
    )


class PriceRecommendation(BaseModel):
    recommended_price: float = Field(
        ...,
        gt=0,
        description="Single best-estimate price in EUR.",
    )
    price_range_min: float = Field(..., gt=0)
    price_range_max: float = Field(..., gt=0)
    data_source: str = Field(
        ...,
        description="Short description of where the estimate came from (e.g., Tavily web search).",
    )

    @field_validator("price_range_max")
    @classmethod
    def max_must_exceed_min(cls, value: float, info) -> float:
        min_value = info.data.get("price_range_min")
        if min_value is not None and value <= min_value:
            raise ValueError("price_range_max must be greater than price_range_min")
        return value