"""Tests for the YouTubeSummarizerService module."""

import unittest
from unittest.mock import MagicMock, patch

from yt_summarizer.service import YouTubeSummarizerService


class TestYouTubeSummarizerService(unittest.TestCase):
    """Tests for the YouTubeSummarizerService class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_notion_client = MagicMock()
        self.mock_youtube_client = MagicMock()
        self.mock_llm_client = MagicMock()
        self.service = YouTubeSummarizerService(
            token="mock_token",
            notion_db_id="mock_db_id",
            model="mock_model",
            api_base="mock_api_base",
        )

    @patch("yt_summarizer.service.NotionClient.get_page_properties_from_database")
    @patch("yt_summarizer.service.logger")
    def test_process_videos_logs_info(self, mock_logger, mock_get_page_properties):
        """Test that processing videos logs the expected info message."""
        mock_get_page_properties.return_value = []
        self.service.get_videos_from_notion_db()
        mock_logger.info.assert_called_with("Successfully processed %d videos", 0)


if __name__ == "__main__":
    unittest.main()
