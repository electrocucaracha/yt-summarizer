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
"""

import logging

import litellm

logger = logging.getLogger(__name__)


class Client:
    """Client for interacting with Language Models.

    Wraps LiteLLM to provide high-level methods for analyzing YouTube video
    transcripts, including summarization and key point extraction.
    """

    def __init__(self, model: str, api_base: str) -> None:
        """Initialize LLM client with model and API configuration.

        Args:
            model: The model identifier (e.g., 'ollama/llama3.2', 'gpt-4').
            api_base: The base URL for the LLM API (e.g., 'http://localhost:11434').
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
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a professional summarization assistant. "
                        "Your task is to generate a concise, accurate summary "
                        "based only on the provided video transcript. "
                        "Return only one well-written paragraph. "
                        "The final output must not exceed 2000 characters, "
                        "including spaces."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Summarize the following video transcript in 3–5 sentences. "
                        "Write a single clear paragraph. "
                        "Do not add any information that is not explicitly stated "
                        "in the transcript. "
                        "Ensure the response is no longer than 2000 characters, "
                        "including spaces.\n\n"
                        f"{text}"
                    ),
                },
            ]
            response = litellm.completion(
                model=self.model,
                messages=messages,
                api_base=self.api_base,
                temperature=0.1,
                stream=False,
            )
            summary = response.choices[0].message.content
            logger.debug(
                "Successfully generated summary of %d characters", len(summary)
            )
            return summary
        except Exception as e:
            logger.error("Failed to generate summary: %s", e)
            raise

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
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a professional content analysis assistant. "
                        "Extract the main points from a video transcript. "
                        "Return only clear bullet points based strictly on the transcript. "
                        "The final output must not exceed 2000 characters, "
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
                        "Ensure the response is no longer than 2000 characters, "
                        "including spaces.\n\n"
                        f"{text}"
                    ),
                },
            ]
            response = litellm.completion(
                model=self.model,
                messages=messages,
                api_base=self.api_base,
                temperature=0.1,
                stream=False,
            )
            main_points = response.choices[0].message.content
            logger.debug(
                "Successfully extracted main points of %d characters",
                len(main_points),
            )
            return main_points
        except Exception as e:
            logger.error("Failed to extract main points: %s", e)
            raise
