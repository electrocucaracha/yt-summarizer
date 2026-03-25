# Copyright (c) 2026
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""YouTube video summarizer application.

This module provides the entry point for the YouTube summarizer CLI application.
It orchestrates fetching videos from a Notion database, processing them through
an LLM to generate summaries and extract main points, and updating the database
with the results. The CLI serves as the user interface for the summarization pipeline.
"""

import contextlib
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import click
import click_spinner

from .llm import LLMConnectionError
from .service import YouTubeSummarizerService


@contextlib.contextmanager
def _temporary_logger_level(logger: logging.Logger, level: int):
    """Temporarily set a logger level while running a scoped operation."""
    previous_level = logger.level
    logger.setLevel(level)
    try:
        yield
    finally:
        logger.setLevel(previous_level)


def _progress_item_label(item) -> str:
    """Render the current item inside Click progress bars without extra echoes."""
    if isinstance(item, tuple) and item:
        return str(item[0])
    return str(getattr(item, "url", item))


def _read_token_from_file(file_path: str) -> str:
    """Read the Notion token from a file.

    Args:
        file_path: Path to the file containing the token.

    Returns:
        The token string (stripped of whitespace).

    Raises:
        FileNotFoundError: If the token file does not exist.
        ValueError: If the token file is empty.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            token = f.read().strip()
            if not token:
                raise ValueError(f"Token file '{file_path}' is empty")
            return token
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Notion token file not found at '{file_path}'. "
            "Please provide a token file or set NOTION_TOKEN environment variable."
        ) from exc


@click.command()
@click.option("--notion-db-id", envvar="NOTION_DATABASE_ID")
@click.option(
    "--notion-token-file",
    default="/etc/notion/secrets.txt",
    envvar="NOTION_TOKEN_FILE",
    help="Path to file containing Notion API token",
)
@click.option("--model", default="ollama/llama3.2", envvar="LLM_MODEL")
@click.option("--api-base", default="http://localhost:11434", envvar="LLM_API_BASE")
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    help="Set the logging level.",
)
@click.option("--playlist-url", required=False, help="YouTube playlist URL to process")
@click.option(
    "--proxy-username",
    required=False,
    envvar="PROXY_USERNAME",
    help="Username for proxy authentication",
)
@click.option(
    "--proxy-password",
    required=False,
    envvar="PROXY_PASSWORD",
    help="Password for proxy authentication",
)
def cli(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    notion_db_id: str,
    notion_token_file: str,
    model: str,
    api_base: str,
    log_level: str,
    playlist_url: str,
    proxy_username: str,
    proxy_password: str,
):
    """Main CLI entry point for the YouTube summarizer.

    Retrieves videos from a Notion database, extracts transcripts and metadata,
    generates summaries and key points using an LLM, and updates the database
    with the results.

    Args:
        notion_db_id: The Notion database ID containing videos to process.
            Can be provided as --notion-db-id flag or NOTION_DATABASE_ID env var.
        notion_token_file: Path to file containing Notion API token
            (default: /etc/notion/secrets.txt). Can be set via NOTION_TOKEN_FILE
            environment variable, or use NOTION_TOKEN env var to override.
        model: The LLM model identifier (default: ollama/llama3.2).
            Can be set via LLM_MODEL environment variable.
        api_base: The LLM API base URL (default: http://localhost:11434).
            Can be set via LLM_API_BASE environment variable.
        log_level: The logging level (default: INFO).
            Can be DEBUG, INFO, WARNING, ERROR, or CRITICAL.

    Raises:
        FileNotFoundError: If the token file does not exist and NOTION_TOKEN is not set.
        ValueError: If the token file is empty and NOTION_TOKEN is not set.
    """
    # Configure logging
    log_file = "yt_summarizer.log"
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s",
        handlers=[
            RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5),
        ],
    )

    # Reduce verbosity for LiteLLM logs
    lite_llm_logger = logging.getLogger("LiteLLM")
    lite_llm_logger.setLevel(max(logging.INFO, getattr(logging, log_level.upper())))

    logger = logging.getLogger(__name__)
    logger.debug("Starting YouTube summarizer with log level: %s", log_level)
    logger.info("Using model: %s", model)
    logger.info("Using API base: %s", api_base)

    click.echo("Starting YouTube summarizer...")
    click.echo(f"Using model: {model}")
    click.echo(f"Using API base: {api_base}")

    completed_successfully = False
    try:
        # Get token from environment variable or read from file
        if "NOTION_TOKEN" in os.environ:
            token = os.environ["NOTION_TOKEN"]
            logger.debug("Using Notion token from NOTION_TOKEN environment variable")
            click.echo("Using Notion token from environment variable.")
        else:
            token = _read_token_from_file(notion_token_file)
            logger.debug("Loaded Notion token from file: %s", notion_token_file)
            click.echo("Loaded Notion token from file.")

        # Initialize the summarizer service
        click.echo("Initializing YouTube summarizer service...")
        service = YouTubeSummarizerService(
            notion_db_id=notion_db_id,
            token=token,
            model=model,
            api_base=api_base,
            proxy_username=proxy_username,
            proxy_password=proxy_password,
        )

        videos = {}
        click.echo("Fetching videos from Notion database...")
        with click_spinner.spinner():
            for page in service.get_videos_from_notion_db():
                logger.info("Fetching page: %s", page.url)
                videos[page.url] = page

        # Process the playlist if provided
        if playlist_url:
            click.echo(f"Processing playlist: {playlist_url}")
            logger.info("Processing playlist: %s", playlist_url)
            for video in service.get_videos_from_playlist(playlist_url):
                if video.url in videos:
                    logger.info(
                        "Video '%s' already exists in Notion database, skipping",
                        video.url,
                    )
                else:
                    videos[video.url] = video

        # Process videos with progress bar
        with _temporary_logger_level(lite_llm_logger, logging.WARNING):
            with click.progressbar(
                videos.items(),
                label="Processing videos",
                item_show_func=_progress_item_label,
            ) as bar:
                for url, video in bar:
                    logger.info("Processing and storing the video: %s", url)
                    service.upsert_video(video)
        completed_successfully = True
    except LLMConnectionError as exc:
        logger.error("LLM endpoint is unavailable: %s", str(exc))
        click.echo(f"LLM connection error: {exc}", err=True)
        sys.exit(1)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("An unexpected error occurred: %s", str(e))
        logger.debug("Exception details:", exc_info=True)
        click.echo("Application encountered an error and will exit.", err=True)
        sys.exit(1)
    finally:
        logger.info("Application terminated.")
        if completed_successfully:
            click.echo("YouTube summarizer has completed.")
