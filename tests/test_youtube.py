"""Tests for the YouTube client module."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import requests

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

    @patch("yt_summarizer.youtube.requests.get")
    def test_get_video_title_reads_open_graph_metadata(self, mock_get):
        """The page's Open Graph title should be returned."""
        response = mock_get.return_value
        response.text = '<meta property="og:title" content="Example video">'

        title = self.client.get_video_title(self.mock_url)

        self.assertEqual("Example video", title)
        response.raise_for_status.assert_called_once_with()
        mock_get.assert_called_once_with(
            self.mock_url,
            proxies=self.client.proxy_config.to_requests_dict(),
            timeout=30,
        )

    @patch("yt_summarizer.youtube.requests.get")
    def test_get_video_title_uses_direct_request_without_proxy(self, mock_get):
        response = mock_get.return_value
        response.text = '<meta property="og:title" content="Direct video">'
        client = Client()

        title = client.get_video_title(self.mock_url)

        self.assertEqual("Direct video", title)
        mock_get.assert_called_once_with(self.mock_url, timeout=30)

    @patch("yt_summarizer.youtube.requests.get")
    def test_get_video_title_returns_fallback_when_metadata_is_missing(self, mock_get):
        """Missing title metadata should return the documented fallback."""
        mock_get.return_value.text = "<html><title>Other title</title></html>"

        self.assertEqual("Title not found", self.client.get_video_title(self.mock_url))

    @patch("yt_summarizer.youtube.requests.get")
    def test_get_video_title_returns_fallback_on_request_error(self, mock_get):
        """Request failures should return the documented title fallback."""
        mock_get.side_effect = requests.exceptions.RequestException("offline")

        self.assertEqual("Title not found", self.client.get_video_title(self.mock_url))


if __name__ == "__main__":
    unittest.main()
