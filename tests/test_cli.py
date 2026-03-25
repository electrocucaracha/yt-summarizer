"""Tests for the CLI module."""

import unittest
from unittest.mock import patch

from yt_summarizer import LLMConnectionError, cli
from yt_summarizer.model import YouTubeVideo


class _FakeProgressBar:
    """Minimal context manager that mimics Click's progress bar iterator."""

    def __init__(self, iterable):
        self._iterable = list(iterable)

    def __enter__(self):
        return self._iterable

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class TestCli(unittest.TestCase):
    """Tests for the Click CLI entry point."""

    @patch("yt_summarizer.logging.basicConfig")
    @patch("yt_summarizer._read_token_from_file", return_value="mock_token")
    @patch("yt_summarizer.click.echo")
    @patch("yt_summarizer.click.progressbar")
    @patch("yt_summarizer.YouTubeSummarizerService")
    def test_cli_uses_progress_item_display_without_per_item_echoes(
        self,
        mock_service_cls,
        mock_progressbar,
        mock_echo,
        _mock_read_token,
        _mock_basic_config,
    ):
        """The CLI should show current progress items via the bar, not extra echoes."""
        notion_video = YouTubeVideo(url="https://www.youtube.com/watch?v=video1")
        mock_service = mock_service_cls.return_value
        mock_service.get_videos_from_notion_db.return_value = [notion_video]
        mock_service.get_videos_from_playlist.return_value = []

        progressbar_calls = []

        def fake_progressbar(iterable, **kwargs):
            items = list(iterable)
            progressbar_calls.append({"items": items, **kwargs})
            return _FakeProgressBar(items)

        mock_progressbar.side_effect = fake_progressbar

        cli.callback(
            notion_db_id="mock_db_id",
            notion_token_file="/tmp/mock-token",
            model="ollama/llama3.2",
            api_base="http://localhost:11434",
            log_level="INFO",
            playlist_url=None,
            proxy_username=None,
            proxy_password=None,
        )

        self.assertEqual(len(progressbar_calls), 1)
        self.assertEqual(
            progressbar_calls[0]["item_show_func"]((notion_video.url, notion_video)),
            notion_video.url,
        )
        self.assertNotIn(
            f"Fetching page: {notion_video.url}",
            [call.args[0] for call in mock_echo.call_args_list if call.args],
        )
        self.assertNotIn(
            f"Processing video: {notion_video.url}",
            [call.args[0] for call in mock_echo.call_args_list if call.args],
        )
        mock_service.upsert_video.assert_called_once_with(notion_video)

    @patch("yt_summarizer.logging.basicConfig")
    @patch("yt_summarizer._read_token_from_file", return_value="mock_token")
    @patch("yt_summarizer.click.echo")
    @patch("yt_summarizer.click.progressbar")
    @patch("yt_summarizer.YouTubeSummarizerService")
    def test_cli_exits_with_clear_message_when_llm_endpoint_is_unavailable(
        self,
        mock_service_cls,
        mock_progressbar,
        mock_echo,
        _mock_read_token,
        _mock_basic_config,
    ):
        """The CLI should surface an actionable LLM connection failure."""
        notion_video = YouTubeVideo(url="https://www.youtube.com/watch?v=video1")
        mock_service = mock_service_cls.return_value
        mock_service.get_videos_from_notion_db.return_value = [notion_video]
        mock_service.get_videos_from_playlist.return_value = []
        mock_service.upsert_video.side_effect = LLMConnectionError(
            "Unable to generate summary because the LLM endpoint "
            "'http://localhost:11434' for model 'ollama/llama3.2' is unavailable."
        )
        mock_progressbar.side_effect = lambda iterable, **kwargs: _FakeProgressBar(
            list(iterable)
        )

        with self.assertRaises(SystemExit) as exc_info:
            cli.callback(
                notion_db_id="mock_db_id",
                notion_token_file="/tmp/mock-token",
                model="ollama/llama3.2",
                api_base="http://localhost:11434",
                log_level="INFO",
                playlist_url=None,
                proxy_username=None,
                proxy_password=None,
            )

        self.assertEqual(exc_info.exception.code, 1)
        echo_messages = [call.args[0] for call in mock_echo.call_args_list if call.args]
        self.assertTrue(
            any(
                message.startswith("LLM connection error: Unable to generate summary")
                for message in echo_messages
            )
        )
        self.assertNotIn("YouTube summarizer has completed.", echo_messages)


if __name__ == "__main__":
    unittest.main()
