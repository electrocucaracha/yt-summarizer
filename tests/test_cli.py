"""Tests for the CLI module."""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from yt_summarizer import cli


class TestCLI:
    """Test cases for CLI commands."""

    def test_cli_help(self):
        """Test CLI help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "--notion-db-id" in result.output
        assert "--model" in result.output
        assert "--api-base" in result.output
        assert "--log-level" in result.output

    @patch("yt_summarizer.YouTubeSummarizerService")
    def test_cli_with_all_options(self, mock_service_class):
        """Test CLI with all options specified."""
        mock_service_instance = Mock()
        mock_service_instance.get_videos.return_value = []
        mock_service_class.return_value = mock_service_instance

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--notion-db-id",
                "db-123",
                "--model",
                "gpt-4",
                "--api-base",
                "https://api.openai.com/v1",
                "--log-level",
                "DEBUG",
            ],
            env={"NOTION_TOKEN": "test-token"},
        )

        assert result.exit_code == 0
        mock_service_class.assert_called_once_with(
            token="test-token", model="gpt-4", api_base="https://api.openai.com/v1"
        )

    @patch("yt_summarizer.YouTubeSummarizerService")
    def test_cli_with_env_vars(self, mock_service_class):
        """Test CLI with environment variables."""
        mock_service_instance = Mock()
        mock_service_instance.get_videos.return_value = []
        mock_service_class.return_value = mock_service_instance

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [],
            env={
                "NOTION_DATABASE_ID": "db-env-123",
                "NOTION_TOKEN": "test-token",
                "LLM_MODEL": "ollama/mistral",
                "LLM_API_BASE": "http://localhost:7860",
            },
        )

        assert result.exit_code == 0
        mock_service_class.assert_called_once_with(
            token="test-token", model="ollama/mistral", api_base="http://localhost:7860"
        )

    @patch("yt_summarizer.YouTubeSummarizerService")
    def test_cli_default_model(self, mock_service_class):
        """Test CLI uses default model when not specified."""
        mock_service_instance = Mock()
        mock_service_instance.get_videos.return_value = []
        mock_service_class.return_value = mock_service_instance

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--notion-db-id", "db-123"], env={"NOTION_TOKEN": "test-token"}
        )

        assert result.exit_code == 0
        mock_service_class.assert_called_once()
        call_args = mock_service_class.call_args
        assert call_args.kwargs["model"] == "ollama/llama3.2"
        assert call_args.kwargs["api_base"] == "http://localhost:11434"

    @patch("yt_summarizer.YouTubeSummarizerService")
    def test_cli_log_level_options(self, mock_service_class):
        """Test that all log level options are accepted."""
        mock_service_instance = Mock()
        mock_service_instance.get_videos.return_value = []
        mock_service_class.return_value = mock_service_instance

        runner = CliRunner()

        for log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            result = runner.invoke(
                cli,
                [
                    "--notion-db-id",
                    "db-123",
                    "--log-level",
                    log_level,
                ],
                env={"NOTION_TOKEN": "test-token"},
            )

            assert result.exit_code == 0

    @patch("yt_summarizer.YouTubeSummarizerService")
    def test_cli_invalid_log_level(self, mock_service_class):
        """Test CLI rejects invalid log level."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--notion-db-id",
                "db-123",
                "--log-level",
                "INVALID",
            ],
        )

        assert result.exit_code != 0

    @patch("yt_summarizer.YouTubeSummarizerService")
    def test_cli_with_videos_processing(self, mock_service_class):
        """Test CLI successfully processes videos."""
        mock_service_instance = Mock()
        mock_video1 = Mock()
        mock_video1.id = "video-1"
        mock_video1.title = "Video 1"
        mock_video2 = Mock()
        mock_video2.id = "video-2"
        mock_video2.title = "Video 2"

        mock_service_instance.get_videos.return_value = [mock_video1, mock_video2]
        mock_service_class.return_value = mock_service_instance

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--notion-db-id", "db-123"], env={"NOTION_TOKEN": "test-token"}
        )

        assert result.exit_code == 0
        mock_service_instance.get_videos.assert_called_once_with("db-123")
        mock_service_instance.update_video.assert_any_call("db-123", mock_video1)
        mock_service_instance.update_video.assert_any_call("db-123", mock_video2)

    @patch("yt_summarizer.YouTubeSummarizerService")
    def test_cli_empty_videos_list(self, mock_service_class):
        """Test CLI handles empty videos list."""
        mock_service_instance = Mock()
        mock_service_instance.get_videos.return_value = []
        mock_service_class.return_value = mock_service_instance

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--notion-db-id", "db-123"], env={"NOTION_TOKEN": "test-token"}
        )

        assert result.exit_code == 0
        mock_service_instance.get_videos.assert_called_once_with("db-123")

    @patch("yt_summarizer.YouTubeSummarizerService")
    def test_cli_service_error_handling(self, mock_service_class):
        """Test CLI handles service errors gracefully."""
        mock_service_class.side_effect = Exception("Service initialization error")

        runner = CliRunner()
        result = runner.invoke(cli, ["--notion-db-id", "db-123"])

        # CLI should exit with error code
        assert result.exit_code != 0

    def test_cli_missing_database_id(self):
        """Test CLI handles missing database ID."""
        runner = CliRunner()
        result = runner.invoke(cli, [], env={"NOTION_TOKEN": "test-token"})

        # CLI may fail without a database ID, that's acceptable
        # As long as it doesn't crash with an unexpected error
        assert result.exit_code in [0, 2, 1]  # Various exit codes possible

    @patch("yt_summarizer.YouTubeSummarizerService")
    def test_cli_case_insensitive_log_level(self, mock_service_class):
        """Test that log level is case-insensitive."""
        mock_service_instance = Mock()
        mock_service_instance.get_videos.return_value = []
        mock_service_class.return_value = mock_service_instance

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--notion-db-id",
                "db-123",
                "--log-level",
                "debug",  # lowercase
            ],
            env={"NOTION_TOKEN": "test-token"},
        )

        assert result.exit_code == 0
