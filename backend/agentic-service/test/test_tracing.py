import importlib
import logging
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def tracing_module(monkeypatch):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    module = importlib.import_module("app.agent.tracing")
    module = importlib.reload(module)
    module._client = None  # reset cached client between tests
    return module


# ---------------------------------------------------------------------------
# is_tracing_enabled
# ---------------------------------------------------------------------------


def test_tracing_disabled_when_no_env_vars(tracing_module):
    assert tracing_module.is_tracing_enabled() is False


def test_tracing_enabled_via_langsmith_tracing(tracing_module, monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    assert tracing_module.is_tracing_enabled() is True


def test_tracing_enabled_via_langchain_tracing_v2(tracing_module, monkeypatch):
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    assert tracing_module.is_tracing_enabled() is True


def test_tracing_disabled_when_set_to_false(tracing_module, monkeypatch):
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    assert tracing_module.is_tracing_enabled() is False


# ---------------------------------------------------------------------------
# get_project_name
# ---------------------------------------------------------------------------


def test_get_project_name_defaults_to_wallabot(tracing_module, monkeypatch):
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    assert tracing_module.get_project_name() == "wallabot"


def test_get_project_name_prefers_langchain_project(tracing_module, monkeypatch):
    monkeypatch.setenv("LANGCHAIN_PROJECT", "my-project")
    monkeypatch.setenv("LANGSMITH_PROJECT", "old-name")
    assert tracing_module.get_project_name() == "my-project"


def test_get_project_name_falls_back_to_langsmith_project(tracing_module, monkeypatch):
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)
    monkeypatch.setenv("LANGSMITH_PROJECT", "wallabot-sprint3")
    assert tracing_module.get_project_name() == "wallabot-sprint3"


# ---------------------------------------------------------------------------
# get_client
# ---------------------------------------------------------------------------


def test_get_client_returns_none_when_tracing_disabled(tracing_module):
    assert tracing_module.get_client() is None


def test_get_client_returns_none_when_langsmith_not_installed(tracing_module, monkeypatch):
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setattr(tracing_module, "LangSmithClient", None)
    tracing_module._client = None
    assert tracing_module.get_client() is None


# ---------------------------------------------------------------------------
# log_validation_failure
# ---------------------------------------------------------------------------


def test_log_validation_failure_calls_create_run(tracing_module, monkeypatch):
    mock_client = MagicMock()
    monkeypatch.setattr(tracing_module, "get_client", lambda: mock_client)

    tracing_module.log_validation_failure(
        component="test_agent",
        title="Test Product",
        attempt=1,
        error=ValueError("bad json"),
    )

    mock_client.create_run.assert_called_once()
    kwargs = mock_client.create_run.call_args.kwargs
    assert kwargs["name"] == "wallabot_test_agent_validation_failure"
    assert kwargs["run_type"] == "tool"
    assert kwargs["inputs"]["title"] == "Test Product"
    assert kwargs["inputs"]["attempt"] == 1
    assert kwargs["inputs"]["event"] == "validation_failure"
    assert "ValueError" in kwargs["error"]


def test_log_validation_failure_includes_extra_inputs(tracing_module, monkeypatch):
    mock_client = MagicMock()
    monkeypatch.setattr(tracing_module, "get_client", lambda: mock_client)

    tracing_module.log_validation_failure(
        component="price_agent",
        title="iPhone",
        attempt=2,
        error=ValueError("schema mismatch"),
        extra_inputs={"condition": "Poor"},
    )

    kwargs = mock_client.create_run.call_args.kwargs
    assert kwargs["inputs"]["condition"] == "Poor"
    assert kwargs["inputs"]["attempt"] == 2


def test_log_validation_failure_is_silent_when_client_is_none(tracing_module, monkeypatch):
    monkeypatch.setattr(tracing_module, "get_client", lambda: None)
    # Must not raise
    tracing_module.log_validation_failure("agent", "title", 1, ValueError("err"))


def test_log_validation_failure_does_not_propagate_client_errors(tracing_module, monkeypatch):
    mock_client = MagicMock()
    mock_client.create_run.side_effect = RuntimeError("LangSmith unreachable")
    monkeypatch.setattr(tracing_module, "get_client", lambda: mock_client)

    # Must not raise even when LangSmith itself errors
    tracing_module.log_validation_failure("agent", "title", 1, ValueError("err"))


# ---------------------------------------------------------------------------
# log_latency_exceeded
# ---------------------------------------------------------------------------


def test_log_latency_exceeded_always_logs_warning(tracing_module, monkeypatch, caplog):
    monkeypatch.setattr(tracing_module, "get_client", lambda: None)

    with caplog.at_level(logging.WARNING):
        tracing_module.log_latency_exceeded("price_agent", "iPhone", 35.0, 30.0)

    assert any("latency threshold exceeded" in r.message for r in caplog.records)
    assert any("35.00" in r.message for r in caplog.records)


def test_log_latency_exceeded_calls_create_run(tracing_module, monkeypatch):
    mock_client = MagicMock()
    monkeypatch.setattr(tracing_module, "get_client", lambda: mock_client)

    tracing_module.log_latency_exceeded("price_agent", "iPhone 13", 42.5, 30.0)

    mock_client.create_run.assert_called_once()
    kwargs = mock_client.create_run.call_args.kwargs
    assert kwargs["name"] == "wallabot_price_agent_latency_exceeded"
    assert kwargs["inputs"]["event"] == "latency_exceeded"
    assert kwargs["outputs"]["elapsed_seconds"] == 42.5
    assert kwargs["outputs"]["threshold_seconds"] == 30.0


def test_log_latency_exceeded_is_silent_when_client_is_none(tracing_module, monkeypatch):
    monkeypatch.setattr(tracing_module, "get_client", lambda: None)
    # Must not raise
    tracing_module.log_latency_exceeded("agent", "title", 99.0, 30.0)


def test_log_latency_exceeded_does_not_propagate_client_errors(tracing_module, monkeypatch):
    mock_client = MagicMock()
    mock_client.create_run.side_effect = ConnectionError("network timeout")
    monkeypatch.setattr(tracing_module, "get_client", lambda: mock_client)

    # Must not raise even when LangSmith is unreachable
    tracing_module.log_latency_exceeded("agent", "title", 99.0, 30.0)
