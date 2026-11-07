"""Tests for model-aware prompt token budgets."""

import pytest

from yt_summarizer import token_budget


def test_get_prompt_token_limit_uses_litellm_model_metadata(monkeypatch):
    """Known models use their reported input limit minus response headroom."""
    observed = []

    def get_model_info(**kwargs):
        observed.append(kwargs)
        return {"max_input_tokens": 16_384}

    monkeypatch.setattr(token_budget.litellm, "get_model_info", get_model_info)

    assert token_budget.get_prompt_token_limit("known-model") == 15_360
    assert observed == [{"model": "known-model", "api_base": None}]


def test_get_prompt_token_limit_uses_conservative_fallback(monkeypatch):
    """Unknown models fall back to an 8K context window."""

    def fail(**_kwargs):
        raise RuntimeError("model is not mapped")

    monkeypatch.setattr(token_budget.litellm, "get_model_info", fail)

    assert token_budget.get_prompt_token_limit("custom/model") == 7_168


@pytest.mark.parametrize(
    "reported_limit",
    [None, True, False, 0, -1, 16.0, "16384"],
)
def test_get_prompt_token_limit_ignores_invalid_metadata(monkeypatch, reported_limit):
    """Invalid metadata uses the fallback budget."""
    monkeypatch.setattr(
        token_budget.litellm,
        "get_model_info",
        lambda **_kwargs: {"max_input_tokens": reported_limit},
    )

    assert token_budget.get_prompt_token_limit("custom/model") == 7_168


def test_get_prompt_token_limit_keeps_one_input_token_for_small_context(monkeypatch):
    """A tiny context still allows at least one input token."""
    monkeypatch.setattr(
        token_budget.litellm,
        "get_model_info",
        lambda **_kwargs: {"max_input_tokens": 1},
    )

    assert token_budget.get_prompt_token_limit("small-model") == 1


def test_count_prompt_tokens_includes_complete_messages(monkeypatch):
    """The tokenizer receives system instructions as well as user content."""
    observed = []
    messages = [
        {"role": "system", "content": "Instructions"},
        {"role": "user", "content": "Transcript"},
    ]

    def count(**kwargs):
        observed.append(kwargs)
        return 42

    monkeypatch.setattr(token_budget.litellm, "token_counter", count)

    assert token_budget.count_prompt_tokens("custom/model", messages) == 42
    assert observed == [{"model": "custom/model", "messages": messages}]


@pytest.mark.parametrize("count", [None, 0, -1, True, "100"])
def test_invalid_token_counts_use_byte_estimate(monkeypatch, count, caplog):
    """Invalid counts use a logged, conservative estimate, not a bypass."""
    monkeypatch.setattr(token_budget.litellm, "token_counter", lambda **_kwargs: count)
    messages = [{"role": "user", "content": "\u5b57\u5e55"}]

    assert token_budget.count_prompt_tokens("custom/model", messages) == 22
    assert "byte-based" in caplog.text


def test_tokenizer_failure_uses_byte_estimate(monkeypatch, caplog):
    """Unsupported tokenizers retain an explicit, conservative size check."""

    def fail(**_kwargs):
        raise ValueError("unsupported tokenizer")

    monkeypatch.setattr(token_budget.litellm, "token_counter", fail)

    assert (
        token_budget.count_prompt_tokens(
            "custom/model", [{"role": "user", "content": "hello"}]
        )
        == 21
    )
    assert "unsupported tokenizer" in caplog.text


def test_ollama_window_comes_from_server_and_is_capped(monkeypatch):
    """Ollama models use the server-reported window, capped by the env limit."""
    token_budget._ollama_context_length.cache_clear()
    monkeypatch.delenv("OLLAMA_MAX_CONTEXT", raising=False)
    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"model_info": {"qwen3.context_length": 262_144}}

    def post(url, **kwargs):
        calls.append((url, kwargs["json"]))
        return Response()

    monkeypatch.setattr(token_budget.httpx, "post", post)

    window = token_budget.get_context_window("ollama/qwen3:27b", "http://host:11434/")
    assert window == 32_768
    monkeypatch.setenv("OLLAMA_MAX_CONTEXT", "100000")
    assert token_budget.get_context_window(
        "ollama/qwen3:27b", "http://host:11434/"
    ) == (100_000)
    assert calls == [("http://host:11434/api/show", {"model": "qwen3:27b"})]
    token_budget._ollama_context_length.cache_clear()


def test_ollama_window_falls_back_when_server_unreachable(monkeypatch):
    """An unreachable Ollama server keeps the conservative window."""
    token_budget._ollama_context_length.cache_clear()

    def post(*_args, **_kwargs):
        raise token_budget.httpx.ConnectError("refused")

    monkeypatch.setattr(token_budget.httpx, "post", post)

    assert token_budget.get_context_window("ollama/x", "http://h:1") == 8_192
    token_budget._ollama_context_length.cache_clear()
