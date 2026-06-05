# -*- coding: utf-8 -*-
"""Tests for augur.llm_client - OpenAI/DeepSeek LLM backend."""

import os
import pytest
from unittest.mock import patch, MagicMock

import augur.llm_client as llm


@pytest.fixture(autouse=True)
def _reset_singletons(monkeypatch):
    """Reset module-level client/failure cache between tests."""
    monkeypatch.setattr(llm, "_client", None)
    monkeypatch.setattr(llm, "_client_failed", False)
    yield


# ---------- provider / model configuration ----------

def test_get_model_default(monkeypatch):
    monkeypatch.delenv("AUGUR_CHAT_MODEL", raising=False)
    assert llm._get_model() == "gpt-4o"


def test_get_model_custom(monkeypatch):
    monkeypatch.setenv("AUGUR_CHAT_MODEL", "deepseek-chat")
    assert llm._get_model() == "deepseek-chat"


def test_get_max_tokens_default_and_override(monkeypatch):
    monkeypatch.delenv("AUGUR_CHAT_MAXTOK", raising=False)
    assert llm._get_max_tokens() == llm._DEFAULT_MAX_TOKENS
    monkeypatch.setenv("AUGUR_CHAT_MAXTOK", "512")
    assert llm._get_max_tokens() == 512


# ---------- availability gate ----------

def test_is_llm_available_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert llm.is_llm_available() is False


def test_is_llm_available_with_key_and_sdk(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    fake_openai = MagicMock()
    import sys
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    assert llm.is_llm_available() is True


# ---------- multi-provider fallback (base_url config) ----------

def test_get_client_uses_openai_base_url(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    fake_openai = MagicMock()
    import sys
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    llm._get_client()
    fake_openai.OpenAI.assert_called_once_with(
        api_key="sk-test", base_url="https://api.deepseek.com/v1"
    )


def test_get_client_falls_back_to_default_endpoint(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    fake_openai = MagicMock()
    import sys
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    llm._get_client()
    args, kwargs = fake_openai.OpenAI.call_args
    assert kwargs.get("base_url") is None
    assert kwargs.get("api_key") == "sk-test"


def test_get_client_caches_failure(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    fake_openai = MagicMock()
    fake_openai.OpenAI.side_effect = RuntimeError("boom")
    import sys
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    assert llm._get_client() is None
    fake_openai.OpenAI.assert_called_once()
    # Second call should short-circuit (no extra OpenAI() invocation)
    assert llm._get_client() is None
    assert fake_openai.OpenAI.call_count == 1


# ---------- error handling / soft-fail ----------

def test_llm_persona_reply_returns_none_when_unavailable(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = llm.llm_persona_reply("system", [], "hi", "Warren")
    assert result is None


def test_llm_persona_reply_handles_api_exception(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    fake_openai = MagicMock()
    fake_openai.OpenAI.return_value.chat.completions.create.side_effect = RuntimeError("api down")
    import sys
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    result = llm.llm_persona_reply("system", [], "hi", "Buffett")
    assert result is None


def test_llm_persona_reply_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("AUGUR_CHAT_MODEL", "gpt-4o-mini")
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content="Hello, investor."))]
    fake_openai = MagicMock()
    fake_openai.OpenAI.return_value.chat.completions.create.return_value = fake_resp
    import sys
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    result = llm.llm_persona_reply(
        "You are Buffett.",
        [{"role": "user", "content": "earlier q"},
         {"role": "assistant", "content": "earlier a"}],
        "What now?",
        "Buffett",
    )
    assert result == "Hello, investor."
    # Verify the model and messages wiring
    kwargs = fake_openai.OpenAI.return_value.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "gpt-4o-mini"
    msgs = kwargs["messages"]
    assert msgs[0]["role"] == "system"
    assert "Buffett" in msgs[0]["content"]
    assert msgs[1]["role"] == "user"
    assert msgs[2]["role"] == "assistant"
    assert msgs[-1] == {"role": "user", "content": "What now?"}


def test_llm_persona_reply_empty_content_returns_none(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content="   "))]
    fake_openai = MagicMock()
    fake_openai.OpenAI.return_value.chat.completions.create.return_value = fake_resp
    import sys
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    result = llm.llm_persona_reply("system", [], "hi", "")
    assert result is None
