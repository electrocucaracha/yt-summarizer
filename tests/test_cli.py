"""Tests for the CLI module."""

import logging
import os
import subprocess
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import litellm
import pytest
from click.core import ParameterSource
from click.testing import CliRunner

from yt_summarizer import (
    LLMConnectionError,
    LLMContextWindowError,
    _draw_video_progress,
    _process_videos_concurrently,
    _resolve_api_base,
    _suppress_litellm_output,
    cli,
)
from yt_summarizer.model import YouTubeVideo


@pytest.mark.parametrize("log_level", ["DEBUG", "INFO", "WARNING"])
def test_cli_configures_logging_for_all_modules_with_existing_root_handler(
    tmp_path, log_level
):
    """CLI logging replaces preconfigured handlers and includes worker messages."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    script = """
import logging
from unittest.mock import MagicMock, patch

logging.basicConfig(level=logging.CRITICAL)
from yt_summarizer import cli
from yt_summarizer.model import YouTubeVideo
from click.testing import CliRunner

video = YouTubeVideo(url="https://www.youtube.com/watch?v=video1")
service = MagicMock()
service.get_videos_from_filesystem.return_value = [video]
service.generate_playlist_summary.return_value = "Summary"

def process_video(video, **kwargs):
    for module in ("yt_summarizer", "yt_summarizer.llm", "yt_summarizer.model",
                   "yt_summarizer.notion", "yt_summarizer.okf",
                   "yt_summarizer.service", "yt_summarizer.token_budget",
                   "yt_summarizer.youtube"):
        logger = logging.getLogger(module)
        logger.debug("debug marker")
        logger.info("info marker")
        logger.warning("warning marker")
    return video

service.upsert_video.side_effect = process_video
with patch("yt_summarizer.YouTubeSummarizerService", return_value=service):
    result = CliRunner().invoke(cli, ["--notion-db-id", "", "--output-dir", ".",
                                     "--workers", "1", "--log-level", LOG_LEVEL])
assert result.exit_code == 0, result.output
logging.shutdown()
"""
    subprocess.run(
        [sys.executable, "-c", f"LOG_LEVEL = {log_level!r}\n{script}"],
        capture_output=True,
        check=True,
        cwd=tmp_path,
        env=env,
        text=True,
    )

    log = (tmp_path / "yt_summarizer.log").read_text(encoding="utf-8")
    for module in (
        "yt_summarizer",
        "yt_summarizer.llm",
        "yt_summarizer.model",
        "yt_summarizer.notion",
        "yt_summarizer.okf",
        "yt_summarizer.service",
        "yt_summarizer.token_budget",
        "yt_summarizer.youtube",
    ):
        assert f" - {module} - WARNING - [ThreadPoolExecutor" in log
    assert ("debug marker" in log) == (log_level == "DEBUG")
    assert ("info marker" in log) == (log_level != "WARNING")


def test_dotenv_loads_before_cli_configuration_and_preserves_environment(tmp_path):
    """CLI imports load cwd .env without overriding existing environment values."""
    (tmp_path / ".env").write_text(
        "LLM_MODEL=dotenv/model\nLLM_API_BASE=http://dotenv.example\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.pop("LLM_API_BASE", None)
    env["LLM_MODEL"] = "environment/model"
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from yt_summarizer import cli; "
                "context = cli.make_context('yt_summarizer', []); "
                "print(context.params['model']); print(context.params['api_base']); "
                "context.close()"
            ),
        ],
        capture_output=True,
        check=True,
        cwd=tmp_path,
        env=env,
        text=True,
    )

    assert result.stdout.splitlines() == [
        "environment/model",
        "http://dotenv.example",
    ]


@pytest.mark.parametrize("stage", ["upsert_video", "generate_playlist_summary"])
def test_cli_reports_context_window_failures(monkeypatch, tmp_path, stage):
    """Both video and executive analysis failures surface without reporting success."""
    service = MagicMock()
    video = YouTubeVideo(url="https://www.youtube.com/watch?v=video1")
    service.get_videos_from_filesystem.return_value = [video]
    service.upsert_video.return_value = video
    getattr(service, stage).side_effect = LLMContextWindowError(
        "Use a model with a larger context window."
    )
    monkeypatch.setattr(
        "yt_summarizer.YouTubeSummarizerService", lambda **_kwargs: service
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        cli, ["--notion-db-id", "", "--output-dir", str(tmp_path)]
    )

    assert result.exit_code == 1
    assert "LLM context window error:" in result.output
    assert "larger context window" in result.output
    assert "YouTube summarizer has completed." not in result.output
    service.store_playlist.assert_not_called()
    if stage == "upsert_video":
        assert "1/1 (100%)" not in result.output


def test_cli_processes_videos_concurrently_using_cpu_count_by_default(
    monkeypatch, tmp_path
):
    """The default worker count uses CPU cores and processes videos in parallel."""
    first_video = YouTubeVideo(url="https://www.youtube.com/watch?v=video1")
    second_video = YouTubeVideo(url="https://www.youtube.com/watch?v=video2")
    barrier = threading.Barrier(2)
    service = MagicMock()
    service.get_videos_from_filesystem.return_value = [first_video, second_video]

    def process_video(video, **_kwargs):
        barrier.wait(timeout=5)
        return video

    service.upsert_video.side_effect = process_video
    service.generate_playlist_summary.return_value = "Playlist summary"
    monkeypatch.setattr(
        "yt_summarizer.YouTubeSummarizerService", lambda **_kwargs: service
    )
    monkeypatch.setattr("yt_summarizer.os.cpu_count", lambda: 2)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        cli, ["--notion-db-id", "", "--output-dir", str(tmp_path)]
    )

    assert result.exit_code == 0, result.output
    assert "Using 2 worker(s) (auto-selected from 2 CPU core(s))." in result.output
    assert "Overall  : [--------------------] 0/2 (0%) | 2 remaining" in result.output
    assert "Overall  : [####################] 2/2 (100%) | 0 remaining" in result.output
    for worker in (1, 2):
        assert f"Worker {worker:>2}: [####################] 1/1" in result.output
    assert "\x1b[" not in result.output
    service.generate_playlist_summary.assert_called_once_with(
        [first_video, second_video], playlist_title=None
    )


@pytest.mark.parametrize("interactive", [False, True])
def test_worker_progress_updates_after_each_video(monkeypatch, capsys, interactive):
    """Uneven worker queues update both bar levels once per successful result."""
    videos = {
        str(index): YouTubeVideo(url=f"https://www.youtube.com/watch?v={index}")
        for index in range(5)
    }
    original_urls = list(videos)
    service = MagicMock()
    service.upsert_video.side_effect = lambda video, **_kwargs: video
    snapshots = []

    def draw(completed, totals, *, redraw=False):
        snapshots.append((completed.copy(), totals.copy(), redraw))
        _draw_video_progress(completed, totals, redraw=redraw)

    monkeypatch.setattr("yt_summarizer._draw_video_progress", draw)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: interactive)

    _process_videos_concurrently(service, videos, 2, "Playlist")

    output = capsys.readouterr().out
    assert len(snapshots) == 6
    assert [sum(done) for done, _, _ in snapshots] == list(range(6))
    assert all(totals == [3, 2] for _, totals, _ in snapshots)
    assert snapshots[-1] == ([3, 2], [3, 2], interactive)
    assert list(videos) == original_urls
    assert service.upsert_video.call_count == 5
    assert all(
        call.kwargs["playlist_title"] == "Playlist"
        for call in service.upsert_video.call_args_list
    )
    assert "5/5 (100%) | 0 remaining" in output
    assert ("\\x1b" in repr(output)) == interactive
    if interactive:
        assert output.count("\x1b[3A") == 5
        assert output.count("\x1b[2K") == 15


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
    @patch("yt_summarizer.YouTubeSummarizerService")
    def test_cli_displays_overall_and_worker_progress(
        self,
        mock_service_cls,
        mock_echo,
        _mock_read_token,
        _mock_basic_config,
    ):
        """The CLI displays initial and completed progress for each worker."""
        notion_video = YouTubeVideo(url="https://www.youtube.com/watch?v=video1")
        mock_service = mock_service_cls.return_value
        mock_service.get_videos_from_notion_db.return_value = [notion_video]
        mock_service.get_videos_from_playlist.return_value = []
        mock_service.upsert_video.side_effect = lambda video, playlist_title=None: video

        cli.callback(
            notion_db_id="mock_db_id",
            notion_token_file="/tmp/mock-token",
            output_dir=None,
            model="ollama/llama3.2",
            api_base="http://localhost:11434",
            log_level="INFO",
            playlist_url=None,
            proxy_username=None,
            proxy_password=None,
        )

        messages = [call.args[0] for call in mock_echo.call_args_list if call.args]
        self.assertIn(
            "Overall  : [--------------------] 0/1 (0%) | 1 remaining", messages
        )
        self.assertIn(
            "Overall  : [####################] 1/1 (100%) | 0 remaining", messages
        )
        self.assertIn(
            "Worker  1: [####################] 1/1 (100%) | 0 remaining", messages
        )
        self.assertNotIn(
            f"Fetching page: {notion_video.url}",
            [call.args[0] for call in mock_echo.call_args_list if call.args],
        )
        self.assertNotIn(
            f"Processing video: {notion_video.url}",
            [call.args[0] for call in mock_echo.call_args_list if call.args],
        )
        mock_service.upsert_video.assert_called_once_with(
            notion_video, playlist_title=None
        )
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
                output_dir=None,
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
        mock_service.generate_playlist_summary.assert_not_called()

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
        mock_service.upsert_video.side_effect = lambda video, playlist_title=None: video
        mock_progressbar.side_effect = lambda iterable, **kwargs: _FakeProgressBar(
            list(iterable)
        )

        cli.callback(
            notion_db_id="mock_db_id",
            notion_token_file="/tmp/mock-token",
            output_dir=None,
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

    @patch("yt_summarizer.logging.basicConfig")
    @patch("yt_summarizer._read_token_from_file")
    @patch("yt_summarizer.click.echo")
    @patch("yt_summarizer.click.progressbar")
    @patch("yt_summarizer.YouTubeSummarizerService")
    def test_cli_defaults_to_filesystem_storage_without_notion(
        self,
        mock_service_cls,
        mock_progressbar,
        _mock_echo,
        mock_read_token,
        _mock_basic_config,
    ):
        """Without a Notion database the CLI should store results in the docs bundle."""
        stored_video = YouTubeVideo(url="https://www.youtube.com/watch?v=video1")
        mock_service = mock_service_cls.return_value
        mock_service.get_videos_from_filesystem.return_value = [stored_video]
        mock_service.generate_playlist_summary.return_value = "executive summary"
        mock_service.upsert_video.side_effect = lambda video, playlist_title=None: video
        mock_progressbar.side_effect = lambda iterable, **kwargs: _FakeProgressBar(
            list(iterable)
        )

        cli.callback(
            notion_db_id=None,
            notion_token_file="/tmp/mock-token",
            output_dir=None,
            model="ollama/llama3.2",
            api_base="http://localhost:11434",
            log_level="INFO",
            playlist_url=None,
            proxy_username=None,
            proxy_password=None,
        )

        mock_read_token.assert_not_called()
        mock_service.get_videos_from_notion_db.assert_not_called()
        self.assertEqual("docs", mock_service_cls.call_args.kwargs["output_dir"])
        self.assertIsNone(mock_service_cls.call_args.kwargs["token"])
        mock_service.store_playlist.assert_called_once_with(
            [stored_video],
            playlist_title=None,
            playlist_summary="executive summary",
            playlist_url=None,
        )

    @patch("yt_summarizer.logging.basicConfig")
    @patch("yt_summarizer._read_token_from_file")
    @patch("yt_summarizer.click.progressbar")
    @patch("yt_summarizer.YouTubeSummarizerService")
    def test_cli_output_dir_ignores_notion_database_environment_variable(
        self,
        mock_service_cls,
        mock_progressbar,
        mock_read_token,
        _mock_basic_config,
    ):
        """An explicit filesystem output should not require ambient Notion config."""
        mock_service = mock_service_cls.return_value
        mock_service.generate_playlist_summary.return_value = "executive summary"
        mock_progressbar.side_effect = lambda iterable, **kwargs: _FakeProgressBar(
            list(iterable)
        )

        result = CliRunner().invoke(
            cli,
            ["--output-dir", "docs"],
            env={"NOTION_DATABASE_ID": "ambient-database-id"},
        )

        self.assertEqual(0, result.exit_code, result.output)
        mock_read_token.assert_not_called()
        self.assertIsNone(mock_service_cls.call_args.kwargs["notion_db_id"])
        self.assertIsNone(mock_service_cls.call_args.kwargs["token"])
        self.assertEqual("docs", mock_service_cls.call_args.kwargs["output_dir"])

    @patch("yt_summarizer.logging.basicConfig")
    @patch("yt_summarizer._read_token_from_file")
    @patch("yt_summarizer.click.echo")
    @patch("yt_summarizer.click.progressbar")
    @patch("yt_summarizer.YouTubeSummarizerService")
    def test_cli_skips_already_summarized_videos_from_filesystem(
        self,
        mock_service_cls,
        mock_progressbar,
        mock_echo,
        _mock_read_token,
        _mock_basic_config,
    ):
        """CLI should load existing filesystem videos and skip re-summarizing them."""
        summarized_video = YouTubeVideo(
            url="https://www.youtube.com/watch?v=video1",
            title="Video 1",
            summary="Existing summary",
            main_points="| # | Main point |\n| -: | - |\n| 1 | point 1 |",
        )
        new_video = YouTubeVideo(
            url="https://www.youtube.com/watch?v=video2",
            title="Video 2",
        )
        mock_service = mock_service_cls.return_value
        mock_service.get_videos_from_filesystem.return_value = [summarized_video]
        mock_service.get_videos_from_playlist.return_value = {
            "title": "Cloud Native Series",
            "videos": [
                YouTubeVideo(
                    url="https://www.youtube.com/watch?v=video1", title="Video 1"
                ),
                new_video,
            ],
        }
        mock_service.upsert_video.side_effect = lambda video, playlist_title=None: video
        mock_service.generate_playlist_summary.return_value = "Playlist summary"
        mock_progressbar.side_effect = lambda iterable, **kwargs: _FakeProgressBar(
            list(iterable)
        )

        cli.callback(
            notion_db_id=None,
            notion_token_file="/tmp/mock-token",
            output_dir="docs",
            model="ollama/llama3.2",
            api_base="http://localhost:11434",
            log_level="INFO",
            playlist_url="https://youtube.com/playlist?list=series1",
            proxy_username=None,
            proxy_password=None,
        )

        echo_messages = [call.args[0] for call in mock_echo.call_args_list if call.args]
        self.assertIn("Skipped 1 video(s) already summarized.", echo_messages)
        self.assertIn(
            "Added 1 new video(s) from playlist to processing queue.", echo_messages
        )

    def test_resolve_api_base_uses_provider_default_for_github_copilot(self):
        """GitHub Copilot models should not inherit the Ollama default base URL."""
        self.assertIsNone(_resolve_api_base("github_copilot/gpt-4", None))
        self.assertIsNone(
            _resolve_api_base(
                "github_copilot/gpt-4",
                "http://example.invalid",
                api_base_source=ParameterSource.ENVIRONMENT,
            )
        )
        self.assertEqual(
            "http://example.invalid",
            _resolve_api_base(
                "github_copilot/gpt-4",
                "http://example.invalid",
                api_base_source=ParameterSource.COMMANDLINE,
            ),
        )
        self.assertEqual(
            "http://localhost:11434", _resolve_api_base("ollama/llama3.2", None)
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
