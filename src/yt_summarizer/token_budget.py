# Copyright (c) 2026
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Resolve safe prompt budgets from LiteLLM model metadata."""

import functools
import logging
import os

import httpx
import litellm

logger = logging.getLogger(__name__)

DEFAULT_MAX_INPUT_TOKENS = 8_192
RESPONSE_TOKEN_RESERVE = 1_024
# Ollama allocates KV cache for the whole window, so cap very large native windows.
DEFAULT_OLLAMA_MAX_CONTEXT = 32_768


def count_prompt_tokens(model: str, messages: list[dict[str, str]]) -> int:
    """Count the complete prompt, using a conservative fallback if needed."""
    try:
        count = litellm.token_counter(model=model, messages=messages)
        if isinstance(count, int) and not isinstance(count, bool) and count > 0:
            return count
    # Provider tokenizer failures must retain the conservative budget guard.
    except Exception as exc:  # noqa: BLE001 # pylint: disable=broad-exception-caught
        logger.warning("Unable to count prompt tokens for model '%s': %s", model, exc)

    logger.warning("Using UTF-8 byte-based prompt token estimate for model '%s'", model)
    return sum(len(message["content"].encode("utf-8")) + 16 for message in messages)


@functools.cache
def _ollama_context_length(model: str, api_base: str) -> int | None:
    """Ask the Ollama server for the model's native context length."""
    name = model.split("/", 1)[1] if "/" in model else model
    try:
        response = httpx.post(
            f"{api_base.rstrip('/')}/api/show", json={"model": name}, timeout=10
        )
        response.raise_for_status()
        info = response.json().get("model_info", {})
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "Unable to query Ollama context length for '%s' at %s: %s",
            name,
            api_base,
            exc,
        )
        return None
    for key, value in info.items():
        if key.endswith(".context_length") and isinstance(value, int) and value > 0:
            return value
    logger.warning("Ollama reported no context_length for '%s' at %s", name, api_base)
    return None


def _ollama_max_context() -> int:
    """Return the configured cap for the Ollama context window."""
    try:
        return max(1, int(os.environ["OLLAMA_MAX_CONTEXT"]))
    except (KeyError, ValueError):
        return DEFAULT_OLLAMA_MAX_CONTEXT


def get_context_window(model: str, api_base: str | None = None) -> int:
    """Return the context window (tokens) to use for ``model``.

    Ollama models are asked directly for their native window, capped by
    ``OLLAMA_MAX_CONTEXT`` (default 32768). Other providers use LiteLLM metadata.
    Unknown models use a conservative 8K fallback.
    """
    window = DEFAULT_MAX_INPUT_TOKENS
    source = "fallback"

    if model.startswith(("ollama/", "ollama_chat/")) and api_base:
        native = _ollama_context_length(model, api_base)
        if native:
            window = min(native, _ollama_max_context())
            source = f"ollama server (native {native})"
    else:
        try:
            model_info = litellm.get_model_info(model=model, api_base=api_base)
            reported_limit = model_info.get("max_input_tokens")
            if (
                isinstance(reported_limit, int)
                and not isinstance(reported_limit, bool)
                and reported_limit > 0
            ):
                window = reported_limit
                source = "litellm metadata"
        # Unknown provider metadata must retain the conservative context fallback.
        # pylint: disable-next=broad-exception-caught
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Unable to resolve context window for model '%s' (api_base=%s): %s",
                model,
                api_base,
                exc,
            )

    logger.debug("Context window for model '%s': %d tokens (%s)", model, window, source)
    return window


def get_prompt_token_limit(model: str, api_base: str | None = None) -> int:
    """Return a safe input-token budget for ``model``."""
    return max(1, get_context_window(model, api_base) - RESPONSE_TOKEN_RESERVE)
