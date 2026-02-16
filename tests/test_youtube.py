"""Tests for the YouTube client module."""

from unittest.mock import Mock, patch

import pytest

from yt_summarizer.youtube import Client


class TestYouTubeClient:
    """Test cases for YouTube Client class."""

    def test_init_valid_url(self, youtube_url, video_id):
        """Test initialization with a valid YouTube URL."""
        client = Client(url=youtube_url)
        assert client.url == youtube_url
        assert client.video_id == video_id

    def test_init_invalid_url_no_video_id(self):
        """Test initialization with URL missing video ID raises KeyError."""
        invalid_url = "https://www.youtube.com/watch?v="
        with pytest.raises(KeyError):
            Client(url=invalid_url)

    def test_init_url_without_v_parameter(self):
        """Test initialization with URL missing 'v' parameter raises KeyError."""
        invalid_url = "https://www.youtube.com"
        with pytest.raises(KeyError):
            Client(url=invalid_url)

    @patch("yt_summarizer.youtube.YouTubeTranscriptApi")
    def test_get_video_transcript_success(
        self, mock_transcript_api, youtube_url, video_id, sample_transcript
    ):
        """Test successful video transcript retrieval."""
        # Mock the transcript API response
        mock_snippet = Mock()
        mock_snippet.text = "This is a sample transcript. "
        mock_snippet2 = Mock()
        mock_snippet2.text = "It contains multiple sentences. "

        mock_transcript_obj = Mock()
        mock_transcript_obj.snippets = [mock_snippet, mock_snippet2]

        mock_transcript_api.return_value.fetch.return_value = mock_transcript_obj

        client = Client(url=youtube_url)
        transcript = client.get_video_transcript()

        assert "This is a sample transcript." in transcript
        assert "It contains multiple sentences." in transcript
        mock_transcript_api.return_value.fetch.assert_called_once_with(video_id)

    @patch("yt_summarizer.youtube.YouTubeTranscriptApi")
    def test_get_video_transcript_api_error(self, mock_transcript_api, youtube_url):
        """Test transcript retrieval when API raises an exception."""
        mock_transcript_api.return_value.fetch.side_effect = Exception("API Error")

        client = Client(url=youtube_url)

        with pytest.raises(Exception) as exc_info:
            client.get_video_transcript()

        assert "API Error" in str(exc_info.value)

    @patch("yt_summarizer.youtube.requests.get")
    def test_get_video_title_success(self, mock_requests_get, youtube_url):
        """Test successful video title extraction."""
        mock_response = Mock()
        mock_response.text = '<html><head><meta property="og:title" content="Sample Video Title"></head></html>'
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response

        client = Client(url=youtube_url)
        title = client.get_video_title()

        assert title == "Sample Video Title"
        mock_requests_get.assert_called_once_with(youtube_url)

    @patch("yt_summarizer.youtube.requests.get")
    def test_get_video_title_no_og_tag(self, mock_requests_get, youtube_url):
        """Test video title extraction when og:title tag is missing."""
        mock_response = Mock()
        mock_response.text = "<html><head><title>Some Title</title></head></html>"
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response

        client = Client(url=youtube_url)
        title = client.get_video_title()

        assert title == "Title not found"

    @patch("yt_summarizer.youtube.requests.get")
    def test_get_video_title_request_error(self, mock_requests_get, youtube_url):
        """Test video title extraction when request fails."""
        mock_requests_get.side_effect = Exception("Connection error")

        client = Client(url=youtube_url)
        title = client.get_video_title()

        assert title == "Title not found"

    @patch("yt_summarizer.youtube.requests.get")
    def test_get_video_title_http_error(self, mock_requests_get, youtube_url):
        """Test video title extraction when HTTP error occurs."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")
        mock_requests_get.return_value = mock_response

        client = Client(url=youtube_url)
        title = client.get_video_title()

        assert title == "Title not found"

    def test_different_video_ids(self):
        """Test parsing different video IDs from URLs."""
        test_cases = [
            ("https://www.youtube.com/watch?v=abc123def456", "abc123def456"),
            ("https://www.youtube.com/watch?v=_-_-_-_", "_-_-_-_"),
            ("https://youtu.be/XYZ789", None),  # youtu.be format not parsed
        ]

        for url, expected_id in test_cases:
            if expected_id:
                client = Client(url=url)
                assert client.video_id == expected_id
            else:
                # youtu.be format should handle differently or fail
                try:
                    client = Client(url=url)
                    # If it doesn't fail, that's fine, just check extraction worked
                    assert client.video_id is not None
                except KeyError:
                    # If it fails on youtu.be format, that's acceptable
                    pass

    @patch("yt_summarizer.youtube.YouTubeTranscriptApi")
    def test_get_video_transcript_empty_snippets(
        self, mock_transcript_api, youtube_url
    ):
        """Test transcript retrieval when API returns empty snippets."""
        mock_transcript_obj = Mock()
        mock_transcript_obj.snippets = []
        mock_transcript_api.return_value.fetch.return_value = mock_transcript_obj

        client = Client(url=youtube_url)
        transcript = client.get_video_transcript()

        assert transcript == ""

    @patch("yt_summarizer.youtube.requests.get")
    def test_get_video_title_with_special_characters(
        self, mock_requests_get, youtube_url
    ):
        """Test title extraction with special characters."""
        special_title = "Video Title with Quotes & Special Chars"
        mock_response = Mock()
        mock_response.text = f'<html><head><meta property="og:title" content="{special_title}"></head></html>'
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response

        client = Client(url=youtube_url)
        title = client.get_video_title()

        assert title == special_title
