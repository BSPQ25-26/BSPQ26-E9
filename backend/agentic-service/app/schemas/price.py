from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PriceRequest(BaseModel):
    """Product data sent by the seller to request a price recommendation."""

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
    condition: Literal["New", "Like New", "Good", "Fair", "Poor"] = Field(
        ...,
        description=(
            "Physical condition of the item. Accepted values: "
            "`New`, `Like New`, `Good`, `Fair`, `Poor`. "
            "Condition is the primary factor in price adjustment — "
            "Poor condition can reduce the price by up to 75 % compared to New."
        ),
        examples=["Good"],
    )


class PriceRecommendation(BaseModel):
    """Price estimate returned by the Wallabot agent."""

    recommended_price: float = Field(
        ...,
        gt=0,
        description="Single best-estimate selling price in EUR.",
        examples=[420.0],
    )
    price_range_min: float = Field(
        ...,
        gt=0,
        description="Lower bound of the estimated price range in EUR.",
        examples=[350.0],
    )
    price_range_max: float = Field(
        ...,
        gt=0,
        description=(
            "Upper bound of the estimated price range in EUR. "
            "Always strictly greater than `price_range_min`."
        ),
        examples=[500.0],
    )
    data_source: str = Field(
        ...,
        description=(
            "Brief description of the data used to produce the estimate. "
            "Set to `'fallback: no market data found'` when Tavily returned no results "
            "and the estimate is based solely on LLM training data."
        ),
        examples=["Tavily search: iPhone 13 Pro 128GB Good second-hand price EUR"],
    )

    @field_validator("price_range_max")
    @classmethod
    def max_must_exceed_min(cls, value: float, info) -> float:
        min_value = info.data.get("price_range_min")
        if min_value is not None and value <= min_value:
            raise ValueError("price_range_max must be greater than price_range_min")
        return value
