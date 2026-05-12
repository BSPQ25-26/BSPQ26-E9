import importlib

import pytest
from langchain_core.exceptions import OutputParserException
from pydantic import ValidationError

from app.schemas.price import PriceRecommendation, PriceRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class MockChainFromResult:
    """Returns a fixed PriceRecommendation, capturing the last payload."""

    def __init__(self, result: PriceRecommendation):
        self._result = result
        self.last_payload = None

    def invoke(self, payload, **kwargs):
        self.last_payload = dict(payload)
        return self._result


class MockFailingChain:
    """Always raises, used to exhaust retries."""

    def __init__(self, error: Exception):
        self.error = error
        self.call_count = 0

    def invoke(self, payload, **kwargs):
        self.call_count += 1
        raise self.error


class MockProviderFailingChain:
    """Raises a non-parser exception to trigger the provider-failure path."""

    def __init__(self):
        self.call_count = 0

    def invoke(self, payload, **kwargs):
        self.call_count += 1
        raise RuntimeError("upstream LLM unavailable")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def price_agent_module(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    module = importlib.import_module("app.agent.price_agent")
    return importlib.reload(module)


def _valid_recommendation(**kwargs) -> PriceRecommendation:
    defaults = dict(
        recommended_price=450.0,
        price_range_min=380.0,
        price_range_max=520.0,
        data_source="LLM internal estimate",
    )
    defaults.update(kwargs)
    return PriceRecommendation(**defaults)


def _valid_request(**kwargs) -> PriceRequest:
    defaults = dict(
        title="iPhone 13 Pro",
        description="Used for 1 year, minor wear",
        condition="Good",
    )
    defaults.update(kwargs)
    return PriceRequest(**defaults)


# ---------------------------------------------------------------------------
# Test 1 — Valid request returns PriceRecommendation conforming to schema
# ---------------------------------------------------------------------------


def test_valid_request_with_tavily_data_returns_recommendation(price_agent_module, monkeypatch):
    req = _valid_request()
    expected = _valid_recommendation(data_source="Tavily search: iPhone 13 Pro Good second-hand price EUR")
    mock_chain = MockChainFromResult(expected)

    monkeypatch.setattr(price_agent_module, "_chain", mock_chain)
    monkeypatch.setattr(price_agent_module, "_search_tavily", lambda q: "iPhone 13 Pro 128GB used: €420-€500 on Wallapop")

    result = price_agent_module.recommend_price(req)

    assert isinstance(result, PriceRecommendation)
    assert result.recommended_price == 450.0
    assert result.price_range_min == 380.0
    assert result.price_range_max == 520.0
    assert result.price_range_max > result.price_range_min


# ---------------------------------------------------------------------------
# Test 2 — Pydantic validators reject negative prices
# ---------------------------------------------------------------------------


def test_price_recommendation_rejects_negative_recommended_price():
    with pytest.raises(ValidationError) as exc_info:
        PriceRecommendation(
            recommended_price=-10.0,
            price_range_min=5.0,
            price_range_max=20.0,
            data_source="test",
        )
    assert "recommended_price" in str(exc_info.value)


def test_price_recommendation_rejects_negative_range_min():
    with pytest.raises(ValidationError):
        PriceRecommendation(
            recommended_price=10.0,
            price_range_min=-5.0,
            price_range_max=20.0,
            data_source="test",
        )


def test_price_recommendation_rejects_zero_price():
    with pytest.raises(ValidationError):
        PriceRecommendation(
            recommended_price=0.0,
            price_range_min=0.0,
            price_range_max=20.0,
            data_source="test",
        )


# ---------------------------------------------------------------------------
# Test 3 — Pydantic validators reject min > max range
# ---------------------------------------------------------------------------


def test_price_recommendation_rejects_min_greater_than_max():
    with pytest.raises(ValidationError) as exc_info:
        PriceRecommendation(
            recommended_price=50.0,
            price_range_min=100.0,
            price_range_max=50.0,
            data_source="test",
        )
    assert "price_range_max" in str(exc_info.value)


def test_price_recommendation_rejects_min_equal_to_max():
    with pytest.raises(ValidationError):
        PriceRecommendation(
            recommended_price=50.0,
            price_range_min=50.0,
            price_range_max=50.0,
            data_source="test",
        )


# ---------------------------------------------------------------------------
# Test 4 — Tavily empty result → graceful fallback (200, not 500)
# ---------------------------------------------------------------------------


def test_tavily_empty_result_returns_fallback_with_correct_data_source(price_agent_module, monkeypatch):
    req = _valid_request()
    # Chain returns something valid, but data_source will be overridden by the agent
    mock_chain = MockChainFromResult(_valid_recommendation(data_source="LLM internal estimate"))

    monkeypatch.setattr(price_agent_module, "_chain", mock_chain)
    monkeypatch.setattr(price_agent_module, "_search_tavily", lambda q: None)

    result = price_agent_module.recommend_price(req)

    assert isinstance(result, PriceRecommendation)
    assert result.data_source == "fallback: no market data found"
    # Prices must still be valid
    assert result.recommended_price > 0
    assert result.price_range_min > 0
    assert result.price_range_max > result.price_range_min


def test_tavily_empty_does_not_raise(price_agent_module, monkeypatch):
    req = _valid_request()
    monkeypatch.setattr(price_agent_module, "_chain", MockChainFromResult(_valid_recommendation()))
    monkeypatch.setattr(price_agent_module, "_search_tavily", lambda q: None)

    # Must not raise — graceful path
    result = price_agent_module.recommend_price(req)
    assert result is not None


# ---------------------------------------------------------------------------
# Test 5 — Missing required field → 422 (Pydantic ValidationError)
# ---------------------------------------------------------------------------


def test_price_request_missing_title_raises_validation_error():
    with pytest.raises(ValidationError):
        PriceRequest(description="Some description", condition="Good")  # type: ignore[call-arg]


def test_price_request_missing_condition_raises_validation_error():
    with pytest.raises(ValidationError):
        PriceRequest(title="iPhone", description="Some description")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Test 6 — Invalid condition value → 422
# ---------------------------------------------------------------------------


def test_price_request_rejects_invalid_condition():
    with pytest.raises(ValidationError) as exc_info:
        PriceRequest(title="iPhone", description="desc", condition="Broken")
    assert "condition" in str(exc_info.value)


def test_price_request_rejects_empty_condition():
    with pytest.raises(ValidationError):
        PriceRequest(title="iPhone", description="desc", condition="")


def test_price_request_accepts_all_valid_conditions():
    for condition in ("New", "Like New", "Good", "Fair", "Poor"):
        req = PriceRequest(title="iPhone", description="desc", condition=condition)
        assert req.condition == condition


# ---------------------------------------------------------------------------
# Test 7 — Condition "Poor" reflected in prompt context (check call args)
# ---------------------------------------------------------------------------


def test_condition_poor_is_passed_to_chain_payload(price_agent_module, monkeypatch):
    req = _valid_request(condition="Poor")
    mock_chain = MockChainFromResult(_valid_recommendation())

    monkeypatch.setattr(price_agent_module, "_chain", mock_chain)
    monkeypatch.setattr(price_agent_module, "_search_tavily", lambda q: None)

    price_agent_module.recommend_price(req)

    assert mock_chain.last_payload is not None
    assert mock_chain.last_payload["condition"] == "Poor"


def test_condition_is_included_in_tavily_search_query(price_agent_module, monkeypatch):
    req = _valid_request(title="Nike Air Max", condition="Poor")
    captured_queries: list[str] = []

    def capture_query(q: str) -> None:
        captured_queries.append(q)
        return None

    monkeypatch.setattr(price_agent_module, "_chain", MockChainFromResult(_valid_recommendation()))
    monkeypatch.setattr(price_agent_module, "_search_tavily", capture_query)

    price_agent_module.recommend_price(req)

    assert len(captured_queries) == 1
    assert "Poor" in captured_queries[0]
    assert "Nike Air Max" in captured_queries[0]


# ---------------------------------------------------------------------------
# Provider failure → graceful fallback (bonus coverage)
# ---------------------------------------------------------------------------


def test_provider_failure_returns_fallback_not_raises(price_agent_module, monkeypatch):
    req = _valid_request(condition="Fair")

    monkeypatch.setattr(price_agent_module, "_chain", MockProviderFailingChain())
    monkeypatch.setattr(price_agent_module, "_search_tavily", lambda q: None)

    result = price_agent_module.recommend_price(req)

    assert isinstance(result, PriceRecommendation)
    assert result.data_source == "fallback: no market data found"
    assert result.recommended_price > 0


def test_validation_exhaustion_raises(price_agent_module, monkeypatch):
    req = _valid_request()
    failing_chain = MockFailingChain(OutputParserException("bad json"))

    monkeypatch.setattr(price_agent_module, "_chain", failing_chain)
    monkeypatch.setattr(price_agent_module, "_search_tavily", lambda q: "some data")

    with pytest.raises(OutputParserException):
        price_agent_module.recommend_price(req)

    assert failing_chain.call_count == 3
