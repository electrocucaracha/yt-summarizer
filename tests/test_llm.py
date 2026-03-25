"""Tests for the LLM client module."""

import unittest
from unittest.mock import MagicMock, patch

import litellm

from yt_summarizer.llm import Client, LLMConnectionError


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


if __name__ == "__main__":
    unittest.main()
