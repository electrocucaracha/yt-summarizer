"""Tests for the LLM client module."""

import unittest
from unittest.mock import MagicMock, patch

import litellm

from yt_summarizer.llm import (
    CHUNK_CHAR_SIZE,
    EXECUTIVE_SUMMARY_CHAR_LIMIT,
    MAIN_POINTS_CHAR_LIMIT,
    TRANSCRIPT_SUMMARY_CHAR_LIMIT,
    Client,
    LLMConnectionError,
)


class TestLLMClient(unittest.TestCase):
    """Tests for the LLM Client class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_model = "gpt-4"
        self.mock_api_base = "https://api.example.com"
        self.client = Client(model=self.mock_model, api_base=self.mock_api_base)

    def test_initialization(self):
        """Test that the LLM client initializes with the correct attributes."""
        self.assertEqual(self.client.model, self.mock_model)
        self.assertEqual(self.client.api_base, self.mock_api_base)

    @patch("yt_summarizer.llm.litellm.completion")
    def test_summarize_wraps_api_connection_errors(self, mock_completion):
        """Connection failures should become actionable LLM connection errors."""
        mock_completion.side_effect = litellm.exceptions.APIConnectionError(
            message="connection refused",
            llm_provider="ollama",
            model=self.mock_model,
        )

        with self.assertRaises(LLMConnectionError) as exc_info:
            self.client.summarize("Transcript text")

        self.assertIn("LLM endpoint", str(exc_info.exception))
        self.assertIn(self.mock_api_base, str(exc_info.exception))
        self.assertIn(self.mock_model, str(exc_info.exception))

    @patch("yt_summarizer.llm.litellm.completion")
    def test_get_main_points_returns_response_content(self, mock_completion):
        """Successful completions should return the message content."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="- point 1\n- point 2"))]
        )

        self.assertEqual(
            self.client.get_main_points("Transcript text"),
            "- point 1\n- point 2",
        )

    @patch("yt_summarizer.llm.litellm.completion")
    def test_generate_executive_summary_uses_dedicated_prompt(self, mock_completion):
        """Executive summaries should use a synthesis-focused prompt."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Executive summary text"))]
        )

        result = self.client.generate_executive_summary("Summary A\n\nSummary B")

        self.assertEqual(result, "Executive summary text")
        messages = mock_completion.call_args.kwargs["messages"]
        self.assertIn("executive briefing assistant", messages[0]["content"])
        self.assertIn("Create an executive summary", messages[1]["content"])
        self.assertIn("Summary A", messages[1]["content"])
        self.assertIn("Summary B", messages[1]["content"])
        self.assertIn(str(EXECUTIVE_SUMMARY_CHAR_LIMIT), messages[0]["content"])

    @patch("yt_summarizer.llm.litellm.completion")
    def test_generate_executive_summary_includes_playlist_title_context(
        self, mock_completion
    ):
        """Executive summaries should include playlist title context when provided."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Executive summary text"))]
        )

        self.client.generate_executive_summary(
            "Summary A\n\nSummary B", playlist_title="Engineering Weekly"
        )

        messages = mock_completion.call_args.kwargs["messages"]
        self.assertIn(
            "The playlist title is: Engineering Weekly.", messages[1]["content"]
        )

    @patch("yt_summarizer.llm.litellm.completion")
    def test_summarize_includes_transcript_text(self, mock_completion):
        """Summaries should be generated from the supplied transcript text."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="ok"))]
        )

        self.client.summarize("Transcript text")

        summary_messages = mock_completion.call_args.kwargs["messages"]
        self.assertIn("Transcript text", summary_messages[1]["content"])

    @patch("yt_summarizer.llm.litellm.completion")
    def test_completion_omits_api_base_when_not_configured(self, mock_completion):
        """Provider-native models should not be forced onto a custom base URL."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="ok"))]
        )
        client = Client(model="github_copilot/gpt-4", api_base=None)

        client.summarize("Transcript text")

        self.assertNotIn("api_base", mock_completion.call_args.kwargs)

    @patch("yt_summarizer.llm.litellm.completion")
    def test_summarize_and_main_points_prompts_use_updated_limits(
        self, mock_completion
    ):
        """Transcript prompts should advertise the configured character limits."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="ok"))]
        )

        self.client.summarize("Transcript text")
        summary_messages = mock_completion.call_args.kwargs["messages"]
        self.assertIn(
            str(TRANSCRIPT_SUMMARY_CHAR_LIMIT), summary_messages[0]["content"]
        )
        self.assertIn(
            str(TRANSCRIPT_SUMMARY_CHAR_LIMIT), summary_messages[1]["content"]
        )

        self.client.get_main_points("Transcript text")
        main_points_messages = mock_completion.call_args.kwargs["messages"]
        self.assertIn(str(MAIN_POINTS_CHAR_LIMIT), main_points_messages[0]["content"])
        self.assertIn(str(MAIN_POINTS_CHAR_LIMIT), main_points_messages[1]["content"])


class TestSummarizationChain(unittest.TestCase):
    """Tests for the map-reduce summarization chain used by Ollama models."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client(model="ollama/llama3.2", api_base="http://localhost:11434")
        self.long_text = "word " * (CHUNK_CHAR_SIZE // 2)

    def test_chain_enabled_only_for_ollama_models(self):
        """Only locally hosted Ollama models should use the chain."""
        self.assertTrue(self.client.uses_summarization_chain)
        self.assertFalse(Client(model="gpt-4", api_base=None).uses_summarization_chain)

    @patch("yt_summarizer.llm.litellm.completion")
    def test_short_text_skips_the_chain(self, mock_completion):
        """Text that fits the context window should use a single request."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Summary"))]
        )

        self.client.summarize("Short transcript")

        self.assertEqual(mock_completion.call_count, 1)

    @patch("yt_summarizer.llm.litellm.completion")
    def test_long_text_is_chunked_and_reduced(self, mock_completion):
        """Long text should be summarized per chunk before the final prompt."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Partial summary"))]
        )

        self.client.summarize(self.long_text)

        self.assertGreater(mock_completion.call_count, 1)
        chunk_messages = mock_completion.call_args_list[0].kwargs["messages"]
        self.assertIn("part 1 of", chunk_messages[1]["content"])
        self.assertLessEqual(len(chunk_messages[1]["content"]), CHUNK_CHAR_SIZE + 500)

        final_messages = mock_completion.call_args.kwargs["messages"]
        self.assertIn("Partial summary", final_messages[1]["content"])

    @patch("yt_summarizer.llm.litellm.completion")
    def test_chain_stops_when_text_does_not_shrink(self, mock_completion):
        """Non-shrinking chunk summaries must not loop indefinitely."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="x" * CHUNK_CHAR_SIZE))]
        )

        self.client.summarize(self.long_text)

        self.assertLessEqual(mock_completion.call_count, 4)


class TestDirectCompletionBehavior(unittest.TestCase):
    """Models without a small context window should get one direct completion."""

    @patch("yt_summarizer.llm.litellm.completion")
    def test_non_ollama_model_sends_full_text(self, mock_completion):
        """Hosted models with large contexts should receive the untouched text."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Summary"))]
        )
        client = Client(model="gpt-4", api_base=None)
        long_text = "word " * 2000

        client.summarize(long_text)

        self.assertEqual(mock_completion.call_count, 1)
        self.assertIn(
            long_text, mock_completion.call_args.kwargs["messages"][1]["content"]
        )


if __name__ == "__main__":
    unittest.main()
