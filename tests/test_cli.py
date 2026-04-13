"""Tests for the CLI module."""

import logging
import unittest
from unittest.mock import patch

import litellm

from yt_summarizer import LLMConnectionError, _suppress_litellm_output, cli
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
        mock_service.generate_playlist_summary.assert_called_once_with(
            [notion_video], playlist_title=None
        )
        self.assertIn(
            "Generating executive summary...",
            [call.args[0] for call in mock_echo.call_args_list if call.args],
        )

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
        mock_service.generate_playlist_summary.assert_called_once_with(
            [notion_video], playlist_title=None
        )
        self.assertIn("Generating executive summary...", echo_messages)

    @patch("yt_summarizer.logging.basicConfig")
    @patch("yt_summarizer._read_token_from_file", return_value="mock_token")
    @patch("yt_summarizer.click.echo")
    @patch("yt_summarizer.click.progressbar")
    @patch("yt_summarizer.YouTubeSummarizerService")
    def test_cli_passes_playlist_title_to_executive_summary(
        self,
        mock_service_cls,
        mock_progressbar,
        _mock_echo,
        _mock_read_token,
        _mock_basic_config,
    ):
        """The CLI should provide playlist title context to the executive summary."""
        notion_video = YouTubeVideo(url="https://www.youtube.com/watch?v=video1")
        playlist_video = YouTubeVideo(url="https://www.youtube.com/watch?v=video2")
        mock_service = mock_service_cls.return_value
        mock_service.get_videos_from_notion_db.return_value = [notion_video]
        mock_service.get_videos_from_playlist.return_value = {
            "title": "Platform Engineering Weekly",
            "videos": [playlist_video],
        }
        mock_progressbar.side_effect = lambda iterable, **kwargs: _FakeProgressBar(
            list(iterable)
        )

        cli.callback(
            notion_db_id="mock_db_id",
            notion_token_file="/tmp/mock-token",
            model="ollama/llama3.2",
            api_base="http://localhost:11434",
            log_level="INFO",
            playlist_url="https://youtube.com/playlist?list=abc123",
            proxy_username=None,
            proxy_password=None,
        )

        mock_service.generate_playlist_summary.assert_called_once_with(
            [notion_video, playlist_video],
            playlist_title="Platform Engineering Weekly",
        )

    def test_suppress_litellm_output_restores_logger_and_flag_state(self):
        """LiteLLM suppression should restore logger and module state after use."""
        logger = logging.getLogger("LiteLLM")
        logger.setLevel(logging.INFO)
        logger.propagate = True
        litellm.log_level = "DEBUG"
        litellm.set_verbose = True
        litellm.suppress_debug_info = False
        litellm.turn_off_message_logging = False

        expected_level = logger.level
        expected_propagate = logger.propagate
        expected_log_level = litellm.log_level
        expected_set_verbose = litellm.set_verbose
        expected_suppress_debug_info = litellm.suppress_debug_info
        expected_turn_off_message_logging = litellm.turn_off_message_logging

        with _suppress_litellm_output():
            self.assertEqual(logging.ERROR, logging.getLogger("LiteLLM").level)
            self.assertFalse(logging.getLogger("LiteLLM").propagate)
            self.assertEqual("ERROR", litellm.log_level)
            self.assertFalse(litellm.set_verbose)
            self.assertTrue(litellm.suppress_debug_info)
            self.assertTrue(litellm.turn_off_message_logging)

        self.assertEqual(expected_level, logging.getLogger("LiteLLM").level)
        self.assertEqual(expected_propagate, logging.getLogger("LiteLLM").propagate)
        self.assertEqual(expected_log_level, litellm.log_level)
        self.assertEqual(expected_set_verbose, litellm.set_verbose)
        self.assertEqual(expected_suppress_debug_info, litellm.suppress_debug_info)
        self.assertEqual(
            expected_turn_off_message_logging, litellm.turn_off_message_logging
        )


if __name__ == "__main__":
    unittest.main()
