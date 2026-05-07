"""Tests for the YouTube client module."""

import unittest
from unittest.mock import patch

from yt_summarizer.youtube import Client


class Snippet:
    """Minimal valid snippet fixture."""

    def __init__(self, text):
        self.text = text


class InvalidSnippet:
    """Minimal invalid snippet fixture."""

    duration = 5


class Transcript:
    """Minimal transcript fixture."""

    def __init__(self, snippets):
        self._snippets = snippets

    @property
    def snippets(self):
        return iter(self._snippets)


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
        mock_fetch.return_value = Transcript((Snippet("Sample"), Snippet("text")))

        transcript = self.client.get_video_transcript(
            "https://youtube.com/watch?v=mock_id"
        )

        self.assertEqual(transcript, "Sample text")

    @patch("yt_summarizer.youtube.YouTubeTranscriptApi.fetch")
    def test_get_transcript_from_invalid_snippet_iterator_raises(self, mock_fetch):
        """Test that invalid fetched transcript snippets raise a TypeError."""
        mock_fetch.return_value = Transcript((InvalidSnippet(),))

        with self.assertRaisesRegex(TypeError, "Unsupported snippet type encountered."):
            self.client.get_video_transcript("https://youtube.com/watch?v=mock_id")


if __name__ == "__main__":
    unittest.main()
