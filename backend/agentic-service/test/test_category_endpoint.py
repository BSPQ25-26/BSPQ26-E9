import importlib
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from langchain_core.exceptions import OutputParserException

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

# When explicitly enabling live mode, mark the full module as live so
# `pytest -m live` runs both mocked endpoint tests and the real live test.
if os.getenv("RUN_LIVE_TESTS", "false").lower() == "true":
    pytestmark = pytest.mark.live


class MockChainFromLlmText:
    """Simulates the chain by parsing a mocked raw LLM response."""

    def __init__(self, parser, llm_text: str):
        self._parser = parser
        self._llm_text = llm_text
        self.last_payload = None

    def invoke(self, payload):
        self.last_payload = payload
        return self._parser.parse(self._llm_text)


class MockFailingChain:
    """Simulates a chain that always fails to exercise retry exhaustion."""

    def __init__(self, error: Exception):
        self.error = error
        self.call_count = 0
        self.last_payload = None

    def invoke(self, payload):
        self.call_count += 1
        self.last_payload = payload
        raise self.error


class MockProviderFailingChain:
    """Simulates provider/config failures where fallback should be returned."""

    def __init__(self, error: Exception):
        self.error = error
        self.call_count = 0

    def invoke(self, payload):
        self.call_count += 1
        raise self.error


@pytest.fixture
def category_agent_module(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    module = importlib.import_module("app.agent.category_agent")
    return importlib.reload(module)


@pytest.fixture
def price_agent_module(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    module = importlib.import_module("app.agent.price_agent")
    return importlib.reload(module)


@pytest.fixture
def wallabot_app(category_agent_module):
    main_module = importlib.import_module("app.main")
    return importlib.reload(main_module).app


def test_known_product_electronics(category_agent_module, wallabot_app, monkeypatch):
    mock_chain = MockChainFromLlmText(
        category_agent_module._parser,
        '{"suggested_category":"Electronics","confidence":0.92,"is_new_category":false}',
    )
    monkeypatch.setattr(category_agent_module, "_chain", mock_chain)
    client = TestClient(wallabot_app)

    response = client.post(
        "/wallabot/category",
        json={
            "title": "iPhone 13 128GB",
            "description": "Used smartphone, barely scratched.",
            "available_categories": ["Electronics", "Clothing & Accessories", "Other"],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "suggested_category": "Electronics",
        "confidence": 0.92,
        "is_new_category": False,
    }


def test_known_product_clothing(category_agent_module, wallabot_app, monkeypatch):
    mock_chain = MockChainFromLlmText(
        category_agent_module._parser,
        '{"suggested_category":"Clothing & Accessories","confidence":0.88,"is_new_category":false}',
    )
    monkeypatch.setattr(category_agent_module, "_chain", mock_chain)
    client = TestClient(wallabot_app)

    response = client.post(
        "/wallabot/category",
        json={
            "title": "Nike Air Max 90",
            "description": "Barely worn sneakers, size 42, white colorway.",
            "available_categories": ["Electronics", "Clothing & Accessories", "Other"],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "suggested_category": "Clothing & Accessories",
        "confidence": 0.88,
        "is_new_category": False,
    }


def test_missing_title_returns_422(category_agent_module, wallabot_app):
    client = TestClient(wallabot_app)

    response = client.post(
        "/wallabot/category",
        json={
            "description": "Used smartphone, barely scratched.",
            "available_categories": ["Electronics", "Other"],
        },
    )

    assert response.status_code == 422


def test_empty_category_list_returns_422(category_agent_module, wallabot_app):
    client = TestClient(wallabot_app)

    response = client.post(
        "/wallabot/category",
        json={
            "title": "iPhone 13 128GB",
            "description": "Used smartphone, barely scratched.",
            "available_categories": [],
        },
    )

    assert response.status_code == 422


def test_malformed_agent_response_retries_and_500(
    category_agent_module, wallabot_app, monkeypatch
):
    failing_chain = MockFailingChain(OutputParserException("bad json"))
    monkeypatch.setattr(category_agent_module, "_chain", failing_chain)
    client = TestClient(wallabot_app)

    response = client.post(
        "/wallabot/category",
        json={
            "title": "Homemade sourdough starter",
            "description": "Active culture, 200g, ships refrigerated.",
            "available_categories": ["Electronics", "Books & Media"],
        },
    )

    assert response.status_code == 500
    body = response.json()
    assert body["detail"]["error"] == "agent_validation_failure"
    assert (
        body["detail"]["message"]
        == "The request could not be processed due to an internal validation failure."
    )
    assert failing_chain.call_count == 3


def test_provider_failure_returns_fallback_other(
    category_agent_module, wallabot_app, monkeypatch
):
    failing_chain = MockProviderFailingChain(RuntimeError("invalid api key"))
    monkeypatch.setattr(category_agent_module, "_chain", failing_chain)
    client = TestClient(wallabot_app)

    response = client.post(
        "/wallabot/category",
        json={
            "title": "iPhone 13 128GB",
            "description": "Used smartphone, barely scratched.",
            "available_categories": ["Electronics", "Other"],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "suggested_category": "Other",
        "confidence": 0.0,
        "is_new_category": False,
    }
    assert failing_chain.call_count == 1


def test_price_endpoint_returns_recommendation(price_agent_module, wallabot_app, monkeypatch):
    mock_chain = MockChainFromLlmText(
        price_agent_module._parser,
        (
            '{"recommended_price":100.0,"price_range_min":80.0,'
            '"price_range_max":120.0,"data_source":"LLM estimate from product details"}'
        ),
    )
    monkeypatch.setattr(price_agent_module, "_chain", mock_chain)
    client = TestClient(wallabot_app)

    response = client.post(
        "/wallabot/price",
        json={
            "title": "iPhone 13 128GB",
            "description": "Used smartphone, barely scratched.",
            "condition": "Good",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "recommended_price": 100.0,
        "price_range_min": 80.0,
        "price_range_max": 120.0,
        "data_source": "LLM estimate from product details",
    }


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS", "false").lower() != "true",
    reason="Set RUN_LIVE_TESTS=true to run live endpoint tests.",
)
def test_live_category_suggestion():
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is required for live Wallabot tests.")

    main_module = importlib.import_module("app.main")
    app = importlib.reload(main_module).app
    client = TestClient(app)

    response = client.post(
        "/wallabot/category",
        json={
            "title": "iPhone 13 128GB",
            "description": "Used smartphone, barely scratched.",
            "available_categories": [
                "Electronics",
                "Clothing & Accessories",
                "Home & Garden",
                "Sports & Outdoors",
                "Vehicles",
                "Books & Media",
                "Toys & Games",
                "Health & Beauty",
                "Collectibles & Art",
                "Other",
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["suggested_category"].strip() != ""
    assert 0.0 <= body["confidence"] <= 1.0
    assert isinstance(body["is_new_category"], bool)
