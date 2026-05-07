"""Tests for the YouTube client module."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from yt_summarizer.youtube import Client


class TestYouTubeClient(unittest.TestCase):
    """Tests for the YouTube Client class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_url = "https://youtube.com/video123"
        self.client = Client(proxy_username="mock_user", proxy_password="mock_pass")

    @patch("yt_summarizer.youtube.YouTubeTranscriptApi.fetch")
    def test_get_transcript(self, mock_fetch):
        """Test that get_video_transcript returns the transcript text."""
        mock_fetch.return_value = [{"text": "Sample text", "start": 0, "duration": 5}]
        transcript = self.client.get_video_transcript(
            "https://youtube.com/watch?v=mock_id"
        )
        self.assertEqual(transcript, "Sample text")

    @patch("yt_summarizer.youtube.YouTubeTranscriptApi.fetch")
    def test_get_transcript_from_snippet_iterator(self, mock_fetch):
        """Test that fetched transcript snippets are processed in a single pass."""
        mock_fetch.return_value = SimpleNamespace(
            snippets=iter(
                (
                    SimpleNamespace(text="Sample"),
                    SimpleNamespace(text="text"),
                )
            )
        )

        transcript = self.client.get_video_transcript(
            "https://youtube.com/watch?v=mock_id"
        )

        self.assertEqual(transcript, "Sample text")

    @patch("yt_summarizer.youtube.YouTubeTranscriptApi.fetch")
    def test_get_transcript_from_invalid_snippet_iterator_raises(self, mock_fetch):
        """Test that invalid fetched transcript snippets raise a TypeError."""
        mock_fetch.return_value = SimpleNamespace(
            snippets=iter((SimpleNamespace(duration=5),))
        )

        with self.assertRaisesRegex(TypeError, "Unsupported snippet type encountered."):
            self.client.get_video_transcript("https://youtube.com/watch?v=mock_id")


if __name__ == "__main__":
    unittest.main()
