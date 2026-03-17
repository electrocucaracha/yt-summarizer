"""Tests for the LLM client module."""

import unittest

from yt_summarizer.llm import Client


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


if __name__ == "__main__":
    unittest.main()
