"""Tests for the Notion client module."""

import unittest
from unittest.mock import MagicMock

from yt_summarizer.notion import Client


class TestNotionClient(unittest.TestCase):
    """Tests for the Notion Client class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_token = "mock_token"
        self.mock_http_client = MagicMock()
        self.client = Client(token=self.mock_token, client=self.mock_http_client)

    def test_initialization(self):
        """Test that the Notion client initializes with the correct attributes."""
        self.assertIsNotNone(self.client.notion_client)


if __name__ == "__main__":
    unittest.main()
