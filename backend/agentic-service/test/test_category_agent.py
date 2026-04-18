import importlib

import pytest
from langchain_core.exceptions import OutputParserException

from app.schemas.category import CategoryRequest


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


@pytest.fixture
def category_agent_module(monkeypatch):
    # ChatOpenAI is constructed at module import time; provide a dummy key for tests.
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    module = importlib.import_module("app.agent.category_agent")
    return importlib.reload(module)


def test_suggest_category_accepts_valid_mocked_llm_response(category_agent_module, monkeypatch):
    request = CategoryRequest(
        title="iPhone 13",
        description="Used smartphone, 128GB",
        available_categories=["Electronics", "Other"],
    )
    mock_chain = MockChainFromLlmText(
        category_agent_module._parser,
        '{"suggested_category":"Electronics","confidence":0.92,"is_new_category":false}',
    )
    monkeypatch.setattr(category_agent_module, "_chain", mock_chain)

    result = category_agent_module.suggest_category(request)

    assert result.suggested_category == "Electronics"
    assert result.confidence == 0.92
    assert result.is_new_category is False
    assert mock_chain.last_payload["title"] == "iPhone 13"
    assert mock_chain.last_payload["description"] == "Used smartphone, 128GB"
    assert mock_chain.last_payload["available_categories"] == "Electronics, Other"
    assert "format_instructions" in mock_chain.last_payload


def test_suggest_category_raises_on_malformed_json_llm_response(
    category_agent_module, monkeypatch
):
    request = CategoryRequest(
        title="Homemade sourdough starter",
        description="Active culture, 200g, ships refrigerated.",
        available_categories=["Electronics", "Books & Media"],
    )
    mock_chain = MockChainFromLlmText(
        category_agent_module._parser,
        "Category: Baking Supplies (confidence 0.9)",
    )
    monkeypatch.setattr(category_agent_module, "_chain", mock_chain)

    with pytest.raises(OutputParserException):
        category_agent_module.suggest_category(request)


def test_suggest_category_raises_on_validation_failure_llm_response(
    category_agent_module, monkeypatch
):
    request = CategoryRequest(
        title="Homemade sourdough starter",
        description="Active culture, 200g, ships refrigerated.",
        available_categories=["Electronics", "Books & Media"],
    )
    # confidence is out of bounds and suggested_category is empty.
    mock_chain = MockChainFromLlmText(
        category_agent_module._parser,
        '{"suggested_category":"   ","confidence":1.5,"is_new_category":true}',
    )
    monkeypatch.setattr(category_agent_module, "_chain", mock_chain)

    with pytest.raises(OutputParserException) as exc:
        category_agent_module.suggest_category(request)

    assert "suggested_category" in str(exc.value)
    assert "confidence" in str(exc.value)


def test_suggest_category_retries_three_times_before_raising(
    category_agent_module, monkeypatch
):
    request = CategoryRequest(
        title="Homemade sourdough starter",
        description="Active culture, 200g, ships refrigerated.",
        available_categories=["Electronics", "Books & Media"],
    )
    failing_chain = MockFailingChain(OutputParserException("bad json"))
    monkeypatch.setattr(category_agent_module, "_chain", failing_chain)

    with pytest.raises(OutputParserException):
        category_agent_module.suggest_category(request)

    assert failing_chain.call_count == 3
