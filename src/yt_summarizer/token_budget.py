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

import logging

import litellm

logger = logging.getLogger(__name__)

DEFAULT_MAX_INPUT_TOKENS = 8_192
RESPONSE_TOKEN_RESERVE = 1_024


def count_prompt_tokens(model: str, messages: list[dict[str, str]]) -> int:
    """Count the complete prompt, using a conservative fallback if needed."""
    try:
        count = litellm.token_counter(model=model, messages=messages)
        if isinstance(count, int) and not isinstance(count, bool) and count > 0:
            return count
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unable to count prompt tokens for model '%s': %s", model, exc)

    logger.warning("Using UTF-8 byte-based prompt token estimate for model '%s'", model)
    return sum(len(message["content"].encode("utf-8")) + 16 for message in messages)


def get_prompt_token_limit(model: str) -> int:
    """Return a safe input-token budget for ``model``.

    Unknown models use a conservative 8K context-window fallback.
    """
    max_input_tokens = DEFAULT_MAX_INPUT_TOKENS

    try:
        model_info = litellm.get_model_info(model=model)
        reported_limit = model_info.get("max_input_tokens")
        if (
            isinstance(reported_limit, int)
            and not isinstance(reported_limit, bool)
            and reported_limit > 0
        ):
            max_input_tokens = reported_limit
    except Exception as exc:  # noqa: BLE001
        logger.debug("Unable to resolve context window for model '%s': %s", model, exc)

    return max(1, max_input_tokens - RESPONSE_TOKEN_RESERVE)
