"""Tests for the YouTubeSummarizerService module."""

import unittest
from unittest.mock import MagicMock, patch

from yt_summarizer.llm import EXECUTIVE_SUMMARY_CHAR_LIMIT
from yt_summarizer.model import YouTubeVideo
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

    def test_generate_playlist_summary_reduces_summaries_in_chunks_of_25(self):
        """Playlist summaries should be reduced in fixed-size chunks before final summary."""
        videos = [
            YouTubeVideo(url=f"https://example.com/{index}", summary=f"summary-{index}")
            for index in range(60)
        ]
        self.service.llm_client = MagicMock()
        self.service.llm_client.generate_executive_summary.side_effect = [
            "chunk-1",
            "chunk-2",
            "chunk-3",
            "final-summary",
        ]

        result = self.service.generate_playlist_summary(videos)

        self.assertEqual("final-summary", result)
        self.assertEqual(
            4, self.service.llm_client.generate_executive_summary.call_count
        )
        self.assertEqual(
            "\n\n".join(f"summary-{index}" for index in range(25)),
            self.service.llm_client.generate_executive_summary.call_args_list[0].args[
                0
            ],
        )
        self.assertEqual(
            "\n\n".join(f"summary-{index}" for index in range(25, 50)),
            self.service.llm_client.generate_executive_summary.call_args_list[1].args[
                0
            ],
        )
        self.assertEqual(
            "\n\n".join(f"summary-{index}" for index in range(50, 60)),
            self.service.llm_client.generate_executive_summary.call_args_list[2].args[
                0
            ],
        )
        self.assertEqual(
            "chunk-1\n\nchunk-2\n\nchunk-3",
            self.service.llm_client.generate_executive_summary.call_args_list[3].args[
                0
            ],
        )

    def test_generate_playlist_summary_returns_empty_when_no_summaries_exist(self):
        """Playlist summary generation should skip the LLM when no summaries are present."""
        videos = [
            YouTubeVideo(url="https://example.com/1", summary=""),
            YouTubeVideo(url="https://example.com/2", summary="   "),
        ]
        self.service.llm_client = MagicMock()

        result = self.service.generate_playlist_summary(videos)

        self.assertEqual("", result)
        self.service.llm_client.generate_executive_summary.assert_not_called()

    def test_generate_playlist_summary_passes_playlist_title_to_llm(self):
        """Playlist title should be passed to executive summary generation."""
        videos = [YouTubeVideo(url="https://example.com/1", summary="summary-1")]
        self.service.llm_client = MagicMock()
        self.service.llm_client.generate_executive_summary.return_value = (
            "final-summary"
        )

        result = self.service.generate_playlist_summary(
            videos, playlist_title="Engineering Leadership"
        )

        self.assertEqual("final-summary", result)
        self.service.llm_client.generate_executive_summary.assert_called_once_with(
            "summary-1", playlist_title="Engineering Leadership"
        )

    def test_generate_playlist_summary_truncates_to_updated_limit(self):
        """Executive summaries should be capped to the configured character limit."""
        videos = [YouTubeVideo(url="https://example.com/1", summary="summary-1")]
        self.service.llm_client = MagicMock()
        self.service.llm_client.generate_executive_summary.return_value = "x" * (
            EXECUTIVE_SUMMARY_CHAR_LIMIT + 50
        )

        result = self.service.generate_playlist_summary(videos)

        self.assertEqual(EXECUTIVE_SUMMARY_CHAR_LIMIT, len(result))
        self.assertTrue(result.endswith("..."))


if __name__ == "__main__":
    unittest.main()
