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

"""Language Model client for content analysis.

Provides an interface to interact with Large Language Models (LLMs) via LiteLLM
for summarizing YouTube video transcripts and extracting key points and main ideas.
This module abstracts the complexity of LLM interactions for seamless integration.
"""

import logging
from typing import NoReturn

import litellm

from .token_budget import (
    RESPONSE_TOKEN_RESERVE,
    count_prompt_tokens,
    get_prompt_token_limit,
)

logger = logging.getLogger(__name__)
TRANSCRIPT_SUMMARY_CHAR_LIMIT = 2000
MAIN_POINTS_CHAR_LIMIT = 2000
EXECUTIVE_SUMMARY_CHAR_LIMIT = 6000
try:
    from headroom.compress import compress as headroom_compress
except ImportError:  # pragma: no cover - optional runtime fallback
    headroom_compress = None

MAX_CHAIN_PASSES = 5


class LLMConnectionError(RuntimeError):
    """Raised when the configured LLM endpoint cannot be reached."""


class LLMContextWindowError(RuntimeError):
    """Raised when a prompt cannot be reduced to the model's safe input budget."""


def _compress_messages(
    model: str, messages: list[dict[str, str]], prompt_token_limit: int
) -> list[dict[str, str]]:
    """Compress prompt messages with Headroom, preserving the original on failure."""
    if headroom_compress is None:
        logger.debug("Headroom is not installed; sending the prompt uncompressed.")
        return list(messages)

    try:
        result = headroom_compress(
            messages=messages,
            model=model,
            model_limit=prompt_token_limit,
            compress_user_messages=True,
            protect_recent=0,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Headroom compression failed; using original prompt: %s", exc)
        return list(messages)

    if result.tokens_before <= 0:
        logger.debug("Headroom reported no token counts; using original prompt.")
        return list(messages)

    logger.debug(
        "Headroom compressed the prompt from %d to %d tokens using %s",
        result.tokens_before,
        result.tokens_after,
        result.transforms_applied,
    )
    return list(result.messages)


def _split_into_chunks(text: str, size: int) -> list[str]:
    """Split text into chunks of at most ``size`` characters on word boundaries.

    Args:
        text: The text to split.
        size: Maximum number of characters per chunk.

    Returns:
        The ordered list of non-empty chunks.
    """
    chunks: list[str] = []
    remaining = text.strip()
    while len(remaining) > size:
        window = remaining[:size]
        split_at = max(window.rfind("\n"), window.rfind(" "))
        if split_at <= 0:
            split_at = size
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


class Client:
    """Client for interacting with Language Models.

    Wraps LiteLLM to provide high-level methods for analyzing YouTube video
    transcripts, including summarization and key point extraction.
    """

    def __init__(self, model: str, api_base: str | None) -> None:
        """Initialize LLM client with model and API configuration.

        Args:
            model: The model identifier (e.g., 'ollama/llama3.2', 'gpt-4').
            api_base: Optional base URL for the LLM API.
        """
        self.model = model
        self.api_base = api_base
        logger.debug(
            "Initialized LLM client with model: %s, api_base: %s", model, api_base
        )

    def summarize(self, text: str) -> str:
        """Generate a concise summary of the provided text.

        Sends the text to the LLM with a system prompt instructing it to summarize
        the content in 3-5 sentences without adding external information.

        Args:
            text: The transcript or text content to summarize.

        Returns:
            A concise summary of the input text (typically 3-5 sentences).
        """
        logger.info("Generating summary using LLM")
        logger.debug("Summarizing %d characters of text", len(text))
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a professional summarization assistant. "
                    "Your task is to generate a concise, accurate summary "
                    "based only on the provided video transcript. "
                    "Return only one well-written paragraph. "
                    f"The final output must not exceed {TRANSCRIPT_SUMMARY_CHAR_LIMIT} "
                    "characters, "
                    "including spaces. The summary must be in the same language as the input text."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Summarize the following video transcript in 3–5 sentences. "
                    "Write a single clear paragraph. "
                    "Do not add any information that is not explicitly stated "
                    "in the transcript. "
                    f"Ensure the response is no longer than {TRANSCRIPT_SUMMARY_CHAR_LIMIT} "
                    "characters, "
                    "including spaces. "
                    "The summary must be in the same language as the input text.\n\n"
                ),
            },
        ]
        summary = self._complete(
            messages=messages, action="generate summary", text=text
        )
        logger.debug("Successfully generated summary of %d characters", len(summary))
        return summary

    def generate_executive_summary(
        self, text: str, playlist_title: str | None = None
    ) -> str:
        """Generate an executive summary from a set of existing summaries.

        Args:
            text: Combined summaries to synthesize into an executive summary.
            playlist_title: Optional playlist title to use as domain context.

        Returns:
            A concise executive summary focused on themes, outcomes, and implications.
        """
        logger.info("Generating executive summary using LLM")
        logger.debug("Synthesizing executive summary from %d characters", len(text))
        playlist_context = (
            f"The playlist title is: {playlist_title}. Use it as context for the "
            "executive summary when relevant. "
            if playlist_title
            else ""
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an executive briefing assistant. "
                    "Synthesize multiple video summaries into a concise executive "
                    "summary that highlights the most important themes, outcomes, "
                    "risks, opportunities, and notable takeaways. "
                    "Base the response only on the provided summaries. "
                    "Return only a polished executive summary without bullet points "
                    "or preamble. "
                    f"The final output must not exceed {EXECUTIVE_SUMMARY_CHAR_LIMIT} "
                    "characters, "
                    "including spaces."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Create an executive summary from the following video summaries. "
                    "Focus on the most important cross-cutting themes and implications. "
                    "Do not add information that is not explicitly supported by the "
                    "provided summaries. Write a compact executive summary in one or "
                    "two short paragraphs, no longer than "
                    f"{EXECUTIVE_SUMMARY_CHAR_LIMIT} characters, including spaces. "
                    f"{playlist_context}\n\n"
                ),
            },
        ]
        summary = self._complete(
            messages=messages, action="generate executive summary", text=text
        )
        logger.debug(
            "Successfully generated executive summary of %d characters", len(summary)
        )
        return summary

    def get_main_points(self, text: str) -> str:
        """Extract the main points and key takeaways from the provided text.

        Sends the text to the LLM with a system prompt instructing it to extract
        major points as bullet points without adding external information.

        Args:
            text: The transcript or text content to analyze.

        Returns:
            A formatted string with bullet points of the main ideas and takeaways.
        """
        logger.info("Extracting main points using LLM")
        logger.debug("Extracting main points from %d characters of text", len(text))
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a professional content analysis assistant. "
                    "Extract the main points from a video transcript. "
                    "Return only clear bullet points based strictly on the transcript. "
                    f"The final output must not exceed {MAIN_POINTS_CHAR_LIMIT} "
                    "characters, "
                    "including spaces."
                ),
            },
            {
                "role": "user",
                "content": (
                    "From the following transcript, extract the key points as "
                    "concise bullet points. "
                    "Do not include explanations, introductions, or conclusions. "
                    "Do not add any information not explicitly stated in the "
                    "transcript. "
                    f"Ensure the response is no longer than {MAIN_POINTS_CHAR_LIMIT} "
                    "characters, "
                    "including spaces.\n\n"
                ),
            },
        ]
        main_points = self._complete(
            messages=messages, action="extract main points", text=text
        )
        logger.debug(
            "Successfully extracted main points of %d characters",
            len(main_points),
        )
        return main_points

    def _condense(self, text: str, prompt_token_limit: int) -> str:
        """Map context-sized excerpts to summaries and join them in source order."""
        chunks: list[str] = []
        pending = [text]
        while pending:
            chunk = pending.pop()
            # The number of parts cannot exceed the number of characters.
            messages = self._chunk_messages(chunk, len(text), len(text))
            if count_prompt_tokens(self.model, messages) <= prompt_token_limit:
                chunks.append(chunk)
            elif len(chunk) > 1:
                pending.extend(reversed(_split_into_chunks(chunk, len(chunk) // 2)))
            else:
                self._context_error("the chunk instructions exceed the input budget")

        logger.info("Running summarization chain over %d chunks", len(chunks))
        return "\n\n".join(
            self._complete(
                self._chunk_messages(chunk, index, len(chunks)),
                action=f"summarize part {index} of {len(chunks)}",
                allow_condense=False,
            )
            for index, chunk in enumerate(chunks, start=1)
        )

    @staticmethod
    def _chunk_messages(chunk: str, index: int, total: int) -> list[dict[str, str]]:
        """Build the same prompt for chunk sizing and chunk completion."""
        return [
            {
                "role": "system",
                "content": (
                    "You are a professional summarization assistant working on a "
                    "partial excerpt of a longer text. "
                    "Preserve every relevant fact, name, number, and conclusion "
                    "stated in the excerpt, and do not add information that is not "
                    "explicitly present. "
                    "Return only a concise summary shorter than the excerpt, "
                    "in the same language as the excerpt."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"This is part {index} of {total} of a longer text. "
                    "Summarize it densely, keeping all key details so the parts can "
                    "later be merged into a single summary.\n\n"
                    f"{chunk}"
                ),
            },
        ]

    def _context_error(self, reason: str) -> NoReturn:
        """Report an unsafe prompt instead of sending it or truncating the source."""
        message = (
            f"Unable to fit the prompt within the context window for model "
            f"'{self.model}': {reason}. Use a model with a larger context window."
        )
        logger.error(message)
        raise LLMContextWindowError(message)

    def _complete(
        self,
        messages: list[dict[str, str]],
        action: str,
        *,
        text: str = "",
        allow_condense: bool = True,
    ) -> str:
        """Compress, reduce if needed, and send only a context-sized prompt."""
        prompt_token_limit = get_prompt_token_limit(self.model)
        for chain_pass in range(MAX_CHAIN_PASSES + 1):
            full_messages = [
                *messages[:-1],
                {**messages[-1], "content": messages[-1]["content"] + text},
            ]
            prepared = _compress_messages(self.model, full_messages, prompt_token_limit)
            if count_prompt_tokens(self.model, prepared) <= prompt_token_limit:
                break
            if not allow_condense or not text:
                self._context_error("the prompt instructions exceed the input budget")
            if chain_pass == MAX_CHAIN_PASSES:
                self._context_error("the summarization pass limit was reached")
            if count_prompt_tokens(self.model, messages) >= prompt_token_limit:
                self._context_error("the prompt instructions leave no room for content")
            condensed = self._condense(text, prompt_token_limit)
            if count_prompt_tokens(
                self.model, [{"role": "user", "content": condensed}]
            ) >= count_prompt_tokens(self.model, [{"role": "user", "content": text}]):
                self._context_error("summarization stopped reducing the token count")
            text = condensed

        try:
            completion_kwargs = {
                "model": self.model,
                "messages": prepared,
                "temperature": 0.1,
                "stream": False,
                "max_tokens": RESPONSE_TOKEN_RESERVE,
            }
            if self.api_base:
                completion_kwargs["api_base"] = self.api_base

            response = litellm.completion(**completion_kwargs)
        except litellm.exceptions.APIConnectionError as exc:
            endpoint_description = (
                f"'{self.api_base}'"
                if self.api_base
                else "the provider default endpoint"
            )
            message = (
                f"Unable to {action} because the LLM endpoint {endpoint_description} "
                f"for model '{self.model}' is unavailable. "
                "Verify the service is running and reachable, then try again."
            )
            logger.error("%s Original error: %s", message, exc)
            raise LLMConnectionError(message) from exc
        except litellm.exceptions.APIError as exc:
            logger.error("Failed to %s: %s", action, exc)
            raise

        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            message = f"Unable to {action}: model '{self.model}' returned no text."
            logger.error(message)
            raise ValueError(message)
        return content
