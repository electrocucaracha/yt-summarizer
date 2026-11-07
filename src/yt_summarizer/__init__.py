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
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from logging.handlers import RotatingFileHandler
from pathlib import Path

import click
import click_spinner
import litellm
from click.core import ParameterSource
from dotenv import load_dotenv

from .llm import LLMConnectionError, LLMContextWindowError
from .model import YouTubeVideo
from .okf import DEFAULT_ROOT as DEFAULT_OUTPUT_DIR
from .service import YouTubeSummarizerService

load_dotenv(Path.cwd() / ".env")


def _draw_video_progress(
    completed: list[int], totals: list[int], *, redraw: bool = False
) -> None:
    """Render one overall bar and one bar per worker on the caller's thread."""
    if redraw:
        click.echo(f"\x1b[{len(totals) + 1}A", nl=False)
    counts = [(sum(completed), sum(totals)), *zip(completed, totals)]
    for index, (done, total) in enumerate(counts):
        filled = 20 * done // total if total else 20
        percent = 100 * done // total if total else 100
        label = "Overall  " if index == 0 else f"Worker {index:>2}"
        line = (
            f"{label}: [{'#' * filled}{'-' * (20 - filled)}] "
            f"{done}/{total} ({percent}%) | {total - done} remaining"
        )
        click.echo(f"\r\x1b[2K{line}" if redraw else line)


def _process_videos_concurrently(
    service: YouTubeSummarizerService,
    videos: dict[str, YouTubeVideo],
    workers: int,
    playlist_title: str | None,
) -> None:
    """Process round-robin worker queues and update progress after each result."""
    items = list(videos.items())
    queues = [iter(items[index::workers]) for index in range(workers)]
    totals = [len(items[index::workers]) for index in range(workers)]
    completed = [0] * workers
    interactive = sys.stdout.isatty()
    _draw_video_progress(completed, totals)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}

        def submit_next(worker: int) -> None:
            item = next(queues[worker], None)
            if item is not None:
                url, video = item
                logging.getLogger(__name__).info(
                    "Worker %d processing and storing the video: %s", worker + 1, url
                )
                future = executor.submit(
                    service.upsert_video, video, playlist_title=playlist_title
                )
                futures[future] = (worker, url)

        for worker in range(workers):
            submit_next(worker)
        while futures:
            finished, _ = wait(futures, return_when=FIRST_COMPLETED)
            for future in finished:
                worker, url = futures.pop(future)
                videos[url] = future.result()
                completed[worker] += 1
                _draw_video_progress(completed, totals, redraw=interactive)
                submit_next(worker)


def _merge_stored_videos(
    stored_videos: list[YouTubeVideo], videos: dict[str, YouTubeVideo]
) -> None:
    """Merge videos loaded from the filesystem into the in-memory video map."""
    for stored in stored_videos:
        if stored.url not in videos:
            videos[stored.url] = stored
        elif not videos[stored.url].summary and stored.summary:
            videos[stored.url].summary = stored.summary
            videos[stored.url].main_points = stored.main_points


@contextlib.contextmanager
def _temporary_logger_level(logger: logging.Logger, level: int):
    """Temporarily set a logger level while running a scoped operation."""
    previous_level = logger.level
    logger.setLevel(level)
    try:
        yield
    finally:
        logger.setLevel(previous_level)


@contextlib.contextmanager
def _suppress_litellm_output():
    """Temporarily suppress noisy LiteLLM logging during user-facing workflows."""
    logger_names = ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy", "litellm")
    loggers = [logging.getLogger(name) for name in logger_names]
    previous_logger_state = [
        {
            "logger": logger,
            "level": logger.level,
            "propagate": logger.propagate,
        }
        for logger in loggers
    ]
    previous_litellm_state = {
        "log_level": getattr(litellm, "log_level", None),
        "set_verbose": getattr(litellm, "set_verbose", None),
        "suppress_debug_info": getattr(litellm, "suppress_debug_info", None),
        "turn_off_message_logging": getattr(litellm, "turn_off_message_logging", None),
    }

    try:
        for logger in loggers:
            logger.setLevel(logging.ERROR)
            logger.propagate = False

        litellm.log_level = "ERROR"
        litellm.set_verbose = False
        litellm.suppress_debug_info = True
        litellm.turn_off_message_logging = True
        yield
    finally:
        for state in previous_logger_state:
            state["logger"].setLevel(state["level"])
            state["logger"].propagate = state["propagate"]

        litellm.log_level = previous_litellm_state["log_level"]
        litellm.set_verbose = previous_litellm_state["set_verbose"]
        litellm.suppress_debug_info = previous_litellm_state["suppress_debug_info"]
        litellm.turn_off_message_logging = previous_litellm_state[
            "turn_off_message_logging"
        ]


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


def _process_playlist(
    service: YouTubeSummarizerService,
    playlist_url: str,
    videos: dict[str, YouTubeVideo],
    logger: logging.Logger,
    output_dir: str | None = None,
) -> str:
    """Fetch a YouTube playlist and merge new videos into the processing queue.

    Args:
        service: The YouTubeSummarizerService instance.
        playlist_url: URL of the YouTube playlist to process.
        videos: Mapping of video URL → video object to update in place.
        logger: Logger instance for diagnostic messages.
        output_dir: Optional root folder of the OKF bundle.

    Returns:
        The playlist title reported by YouTube.
    """
    click.echo(f"\nProcessing playlist: {playlist_url}")
    logger.info("Processing playlist: %s", playlist_url)
    playlist_data = service.get_videos_from_playlist(playlist_url)
    playlist_title = playlist_data["title"]
    playlist_videos = playlist_data["videos"]

    click.echo(f"Playlist Title: {playlist_title}")
    click.echo(f"Playlist contains {len(playlist_videos)} video(s):")
    for idx, video in enumerate(playlist_videos, 1):
        click.echo(f"  {idx}. {video.title}")
        click.echo(f"     URL: {video.url}")
    click.echo("")

    if output_dir:
        _merge_stored_videos(service.get_videos_from_filesystem(playlist_title), videos)

    added_count = 0
    skipped_count = 0
    for video in playlist_videos:
        existing = videos.get(video.url)
        if (
            existing
            and existing.summary
            and existing.summary != "_Not available yet._"
            and existing.main_points
        ):
            logger.info(
                "Video '%s' already summarized, skipping",
                video.url,
            )
            skipped_count += 1
            if not existing.title and video.title:
                existing.title = video.title
        elif existing:
            if not existing.title and video.title:
                existing.title = video.title
            added_count += 1
        else:
            videos[video.url] = video
            added_count += 1

    click.echo(f"Added {added_count} new video(s) from playlist to processing queue.")
    if skipped_count > 0:
        click.echo(f"Skipped {skipped_count} video(s) already summarized.")

    return playlist_title


def _resolve_api_base(
    model: str,
    api_base: str | None,
    api_base_source: ParameterSource | None = None,
) -> str | None:
    """Resolve the effective API base for the selected model."""
    if (
        api_base
        and (not model.startswith("github_copilot/"))
        or api_base_source == ParameterSource.COMMANDLINE
    ):
        return api_base
    if model.startswith("github_copilot/"):
        return None
    return "http://localhost:11434"


@click.command()
@click.option(
    "--notion-db-id",
    envvar="NOTION_DATABASE_ID",
    show_envvar=True,
    help="Notion database to read and update. Omit to use the local OKF collection.",
)
@click.option(
    "--notion-token-file",
    default="/etc/notion/secrets.txt",
    envvar="NOTION_TOKEN_FILE",
    show_default=True,
    show_envvar=True,
    help="File containing the Notion API token. NOTION_TOKEN takes precedence.",
)
@click.option(
    "--output-dir",
    default=None,
    envvar="OUTPUT_DIR",
    show_envvar=True,
    help=(
        "Root of the local OKF collection used to read and write summaries. "
        "Defaults to 'docs' when no Notion database is configured."
    ),
)
@click.option(
    "--model",
    default="ollama/llama3.2",
    envvar="LLM_MODEL",
    show_default=True,
    show_envvar=True,
    help="LiteLLM model identifier to use for summaries.",
)
@click.option(
    "--api-base",
    default=None,
    envvar="LLM_API_BASE",
    show_envvar=True,
    help=(
        "LLM API base URL. Defaults to localhost:11434, or the provider default "
        "for GitHub Copilot models."
    ),
)
@click.option(
    "--log-level",
    envvar="LOG_LEVEL",
    default="INFO",
    show_default=True,
    type=click.Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    help="Set the logging level.",
)
@click.option(
    "--playlist-url",
    envvar="PLAYLIST_URL",
    required=False,
    help="YouTube playlist URL to add to this run.",
)
@click.option(
    "--proxy-username",
    required=False,
    envvar="PROXY_USERNAME",
    show_envvar=True,
    help="Username for proxy authentication",
)
@click.option(
    "--proxy-password",
    required=False,
    envvar="PROXY_PASSWORD",
    show_envvar=True,
    help="Password for proxy authentication",
)
@click.option(
    "--workers",
    type=click.IntRange(min=1),
    default=None,
    envvar="WORKERS",
    show_envvar=True,
    help="Number of videos to process concurrently (defaults to the CPU core count).",
)
def cli(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-branches
    notion_db_id: str | None,
    notion_token_file: str,
    output_dir: str | None,
    model: str,
    api_base: str | None,
    log_level: str,
    playlist_url: str,
    proxy_username: str,
    proxy_password: str,
    workers: int | None = None,
):
    """Summarize YouTube videos from Notion or a local OKF collection.

    Fetch transcripts, generate per-video and collection summaries, and save
    results to the configured storage.
    """
    # pylint: disable=too-many-locals,too-many-statements
    # Configure logging
    log_file = "yt_summarizer.log"
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s",
        force=True,
        handlers=[
            RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5),
        ],
    )

    logger = logging.getLogger(__name__)
    context = click.get_current_context(silent=True)
    notion_db_id_source = (
        context.get_parameter_source("notion_db_id") if context is not None else None
    )
    if output_dir and notion_db_id_source == ParameterSource.ENVIRONMENT:
        notion_db_id = None
    effective_api_base = _resolve_api_base(
        model,
        api_base,
        api_base_source=(
            context.get_parameter_source("api_base") if context is not None else None
        ),
    )
    logger.debug("Starting YouTube summarizer with log level: %s", log_level)
    logger.info("Using model: %s", model)
    logger.info("Using API base: %s", effective_api_base or "provider default")

    click.echo("Starting YouTube summarizer...")
    click.echo(f"Using model: {model}")
    click.echo(f"Using API base: {effective_api_base or 'provider default'}")

    completed_successfully = False
    playlist_title = None
    try:
        token = None
        if notion_db_id:
            # Get token from environment variable or read from file
            if "NOTION_TOKEN" in os.environ:
                token = os.environ["NOTION_TOKEN"]
                logger.debug(
                    "Using Notion token from NOTION_TOKEN environment variable"
                )
                click.echo("Using Notion token from environment variable.")
            else:
                token = _read_token_from_file(notion_token_file)
                logger.debug("Loaded Notion token from file: %s", notion_token_file)
                click.echo("Loaded Notion token from file.")
        else:
            output_dir = output_dir or DEFAULT_OUTPUT_DIR
            click.echo("Notion is not configured; storing results on the filesystem.")

        if output_dir:
            click.echo(f"Storing results in the OKF bundle at: {output_dir}")

        # Initialize the summarizer service
        click.echo("Initializing YouTube summarizer service...")
        service = YouTubeSummarizerService(
            notion_db_id=notion_db_id,
            token=token,
            model=model,
            api_base=effective_api_base,
            proxy_username=proxy_username,
            proxy_password=proxy_password,
            output_dir=output_dir,
        )

        videos = {}
        if notion_db_id:
            click.echo("Fetching videos from Notion database...")
            with click_spinner.spinner():
                for page in service.get_videos_from_notion_db():
                    logger.info("Fetching page: %s", page.url)
                    videos[page.url] = page

        # Process the playlist if provided
        if playlist_url:
            playlist_title = _process_playlist(
                service, playlist_url, videos, logger, output_dir=output_dir
            )
        elif output_dir:
            click.echo("Fetching videos already stored on the filesystem...")
            _merge_stored_videos(
                service.get_videos_from_filesystem(playlist_title), videos
            )

        # Process videos concurrently; cap workers to the queued video count.
        video_items = list(videos.items())
        cpu_cores = os.cpu_count() or 1
        worker_count = (
            min(workers if workers is not None else cpu_cores, len(video_items))
            if video_items
            else 0
        )
        if workers is None:
            click.echo(
                f"Using {worker_count} worker(s) "
                f"(auto-selected from {cpu_cores} CPU core(s))."
            )
        else:
            click.echo(f"Using {worker_count} worker(s) (from --workers).")

        if video_items:
            with _suppress_litellm_output():
                _process_videos_concurrently(
                    service, videos, worker_count, playlist_title
                )
        click.echo("Generating executive summary...")
        with _suppress_litellm_output(), click_spinner.spinner():
            playlist_summary = service.generate_playlist_summary(
                list(videos.values()), playlist_title=playlist_title
            )
        service.store_playlist(
            list(videos.values()),
            playlist_title=playlist_title,
            playlist_summary=playlist_summary,
            playlist_url=playlist_url,
        )
        click.echo("\nExecutive Summary of the Playlist:")
        click.echo(playlist_summary)
        completed_successfully = True
    except LLMConnectionError as exc:
        logger.error("LLM endpoint is unavailable: %s", str(exc))
        click.echo(f"LLM connection error: {exc}", err=True)
        sys.exit(1)
    except LLMContextWindowError as exc:
        logger.error("LLM context window exhausted: %s", str(exc))
        click.echo(f"LLM context window error: {exc}", err=True)
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
