from unittest.mock import MagicMock

from yt_summarizer.youtube import Client


def test_get_video_transcript():
    youtube_transcript_api_mock = MagicMock()
    youtube_transcript_api_mock.fetch.return_value.snippets = [
        MagicMock(text="Snippet 1"),
        MagicMock(text="Snippet 2"),
    ]

    client = Client()
    client.ytt_api = youtube_transcript_api_mock

    transcript = client.get_video_transcript("https://www.youtube.com/watch?v=abc123")

    assert transcript == "Snippet 1 Snippet 2"
    youtube_transcript_api_mock.fetch.assert_called_once()
