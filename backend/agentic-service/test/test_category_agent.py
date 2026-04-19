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


class MockFailThenSuccessChain:
    """Fails once with parser error, then succeeds to validate retry payload updates."""

    def __init__(self, parser):
        self._parser = parser
        self.call_count = 0
        self.payloads = []

    def invoke(self, payload):
        self.call_count += 1
        self.payloads.append(dict(payload))
        if self.call_count == 1:
            raise OutputParserException("bad json", llm_output="not-json")
        return self._parser.parse(
            '{"suggested_category":"Electronics","confidence":0.91,"is_new_category":false}'
        )


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


def test_suggest_category_injects_retry_feedback_after_first_failure(
    category_agent_module, monkeypatch
):
    request = CategoryRequest(
        title="iPhone 13",
        description="Used smartphone, 128GB",
        available_categories=["Electronics", "Other"],
    )
    flaky_chain = MockFailThenSuccessChain(category_agent_module._parser)
    monkeypatch.setattr(category_agent_module, "_chain", flaky_chain)

    result = category_agent_module.suggest_category(request)

    assert result.suggested_category == "Electronics"
    assert flaky_chain.call_count == 2
    assert flaky_chain.payloads[0]["retry_feedback"] == ""
    assert "Previous response failed schema validation." in flaky_chain.payloads[1][
        "retry_feedback"
    ]


def test_suggest_category_truncates_large_llm_output_in_retry_feedback(
    category_agent_module, monkeypatch
):
    request = CategoryRequest(
        title="iPhone 13",
        description="Used smartphone, 128GB",
        available_categories=["Electronics", "Other"],
    )
    long_output = "x" * 1500
    failing_once = MockFailThenSuccessChain(category_agent_module._parser)

    def invoke_with_large_output(payload):
        failing_once.call_count += 1
        failing_once.payloads.append(dict(payload))
        if failing_once.call_count == 1:
            raise OutputParserException("bad json", llm_output=long_output)
        return category_agent_module._parser.parse(
            '{"suggested_category":"Electronics","confidence":0.91,"is_new_category":false}'
        )

    monkeypatch.setattr(failing_once, "invoke", invoke_with_large_output)
    monkeypatch.setattr(category_agent_module, "_chain", failing_once)

    result = category_agent_module.suggest_category(request)

    assert result.suggested_category == "Electronics"
    retry_feedback = failing_once.payloads[1]["retry_feedback"]
    assert "... [truncated]" in retry_feedback
    assert len(retry_feedback) < 1400


def test_suggest_category_returns_other_fallback_on_provider_failure(
    category_agent_module, monkeypatch
):
    request = CategoryRequest(
        title="iPhone 13",
        description="Used smartphone, 128GB",
        available_categories=["Electronics", "Other"],
    )
    failing_chain = MockProviderFailingChain(RuntimeError("missing api key"))
    monkeypatch.setattr(category_agent_module, "_chain", failing_chain)

    result = category_agent_module.suggest_category(request)

    assert result.suggested_category == "Other"
    assert result.confidence == 0.0
    assert result.is_new_category is False
    assert failing_chain.call_count == 1


def test_suggest_category_returns_first_category_when_other_not_present(
    category_agent_module, monkeypatch
):
    request = CategoryRequest(
        title="iPhone 13",
        description="Used smartphone, 128GB",
        available_categories=["Electronics", "Books & Media"],
    )
    failing_chain = MockProviderFailingChain(RuntimeError("invalid api key"))
    monkeypatch.setattr(category_agent_module, "_chain", failing_chain)

    result = category_agent_module.suggest_category(request)

    assert result.suggested_category == "Electronics"
    assert result.confidence == 0.0
    assert result.is_new_category is False
