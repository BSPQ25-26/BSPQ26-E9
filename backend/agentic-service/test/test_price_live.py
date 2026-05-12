"""
Live price-sanity tests — call real Tavily + OpenAI and verify recommendations
fall within reasonable real-world market ranges.

Run with:
    RUN_LIVE_TESTS=true pytest test/test_price_live.py -v
"""

import os

import pytest

from app.agent.price_agent import recommend_price
from app.schemas.price import PriceRecommendation, PriceRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _skip_if_missing_keys():
    missing = [k for k in ("OPENAI_API_KEY", "TAVILY_API_KEY") if not os.getenv(k)]
    if missing:
        pytest.skip(f"Missing env vars: {', '.join(missing)}")


# ---------------------------------------------------------------------------
# Price-sanity parametrize table
#
# Columns: title, description, condition, price_floor, price_ceiling (EUR)
#
# Ranges are intentionally wide — we test for obvious nonsense, not exact
# market accuracy.  A used iPhone for €1 or €1 000 000 is clearly wrong;
# anything inside the band is considered sane.
# ---------------------------------------------------------------------------

PRICE_SANITY_CASES = [
    pytest.param(
        "iPhone 13 Pro 128GB",
        "Used for one year, minor screen scratches, battery at 87%",
        "Good",
        80.0,
        900.0,
        id="iphone_13_pro_good",
    ),
    pytest.param(
        "MacBook Pro 14-inch M1 Pro 16GB 512GB",
        "Purchased in 2022, no physical damage, charger included",
        "Like New",
        500.0,
        2500.0,
        id="macbook_pro_14_like_new",
    ),
    pytest.param(
        "Nike Air Max 90 size EU 42",
        "Worn around five times, original box included, no sole wear",
        "Like New",
        20.0,
        250.0,
        id="nike_air_max_90_like_new",
    ),
    pytest.param(
        "IKEA KALLAX 2x4 shelf unit white",
        "Six years old, a few scratches, structurally intact",
        "Fair",
        5.0,
        120.0,
        id="ikea_kallax_fair",
    ),
    pytest.param(
        "Sony PlayStation 5 Disc Edition",
        "Includes two DualSense controllers and three games",
        "Good",
        100.0,
        600.0,
        id="ps5_good",
    ),
    pytest.param(
        "Trek FX3 Disc Hybrid Bike",
        "2021 model, new brake pads, some rust on chain, rides well",
        "Fair",
        80.0,
        800.0,
        id="trek_fx3_fair",
    ),
    pytest.param(
        "Harry Potter Complete 7-Book Paperback Set",
        "All books present, some yellowing, no torn pages",
        "Good",
        5.0,
        100.0,
        id="harry_potter_books_good",
    ),
    pytest.param(
        "Levi's 501 Original Jeans size 32x32",
        "Barely worn, washed twice, no fading or damage",
        "Like New",
        10.0,
        150.0,
        id="levis_501_like_new",
    ),
    pytest.param(
        "Dyson V11 Cordless Vacuum Cleaner",
        "Two years old, suction slightly reduced, all attachments present",
        "Good",
        80.0,
        450.0,
        id="dyson_v11_good",
    ),
    pytest.param(
        "Lego Technic Bugatti Chiron 42083",
        "Complete set, all pieces counted, original box and instructions",
        "Good",
        80.0,
        350.0,
        id="lego_bugatti_good",
    ),
    pytest.param(
        "Acoustic Guitar Yamaha F310",
        "Entry-level guitar, a few scratches on body, plays fine",
        "Poor",
        10.0,
        150.0,
        id="yamaha_f310_poor",
    ),
    pytest.param(
        'Samsung 65" QLED 4K TV QN90A',
        "Two years old, works perfectly, remote included, no dead pixels",
        "Good",
        200.0,
        1200.0,
        id="samsung_qled_65_good",
    ),
]


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS", "false").lower() != "true",
    reason="Set RUN_LIVE_TESTS=true to run live price-sanity tests.",
)
@pytest.mark.parametrize("title,description,condition,floor,ceiling", PRICE_SANITY_CASES)
def test_price_is_within_sane_range(title, description, condition, floor, ceiling):
    _skip_if_missing_keys()

    req = PriceRequest(title=title, description=description, condition=condition)
    result = recommend_price(req)

    assert isinstance(result, PriceRecommendation), "recommend_price must return a PriceRecommendation"

    # Schema coherence
    assert result.recommended_price > 0, "recommended_price must be positive"
    assert result.price_range_min > 0, "price_range_min must be positive"
    assert result.price_range_max > result.price_range_min, (
        f"price_range_max ({result.price_range_max}) must exceed price_range_min ({result.price_range_min})"
    )
    assert result.data_source.strip(), "data_source must not be empty"

    # Real-world sanity bounds
    assert result.recommended_price >= floor, (
        f"{title!r} ({condition}): recommended_price {result.recommended_price:.2f} EUR "
        f"is below the floor of {floor:.2f} EUR"
    )
    assert result.recommended_price <= ceiling, (
        f"{title!r} ({condition}): recommended_price {result.recommended_price:.2f} EUR "
        f"exceeds the ceiling of {ceiling:.2f} EUR"
    )


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS", "false").lower() != "true",
    reason="Set RUN_LIVE_TESTS=true to run live price-sanity tests.",
)
def test_condition_affects_price_direction():
    """A New product must be priced higher than the same product in Poor condition."""
    _skip_if_missing_keys()

    product_title = "iPhone 13 Pro 128GB"
    product_description = "Smartphone, 128GB storage"

    result_new = recommend_price(PriceRequest(
        title=product_title,
        description=product_description,
        condition="New",
    ))
    result_poor = recommend_price(PriceRequest(
        title=product_title,
        description=product_description,
        condition="Poor",
    ))

    assert result_new.recommended_price > result_poor.recommended_price, (
        f"Expected New ({result_new.recommended_price:.2f} EUR) > "
        f"Poor ({result_poor.recommended_price:.2f} EUR) for {product_title!r}"
    )


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS", "false").lower() != "true",
    reason="Set RUN_LIVE_TESTS=true to run live price-sanity tests.",
)
def test_tavily_market_data_is_used_when_key_is_set():
    """When TAVILY_API_KEY is present, data_source should not be the fallback string."""
    _skip_if_missing_keys()

    result = recommend_price(PriceRequest(
        title="iPhone 13 Pro 128GB",
        description="Good condition, minor wear",
        condition="Good",
    ))

    assert result.data_source != "fallback: no market data found", (
        "Tavily API key is set but data_source is the fallback string — "
        "Tavily search may not be returning results for this query."
    )


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS", "false").lower() != "true",
    reason="Set RUN_LIVE_TESTS=true to run live price-sanity tests.",
)
def test_price_range_is_not_absurdly_wide():
    """The price range should not span more than 10× — that indicates a hallucination."""
    _skip_if_missing_keys()

    result = recommend_price(PriceRequest(
        title="Samsung Galaxy S23",
        description="Android smartphone, 256GB, minor wear",
        condition="Good",
    ))

    ratio = result.price_range_max / result.price_range_min
    assert ratio <= 10.0, (
        f"Price range is suspiciously wide: min={result.price_range_min:.2f}, "
        f"max={result.price_range_max:.2f} (ratio {ratio:.1f}×)"
    )
