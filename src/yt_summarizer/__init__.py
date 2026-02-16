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
with the results.
"""

import logging
import os

import click

from .service import YouTubeSummarizerService


@click.command()
@click.option("--notion-db-id", envvar="NOTION_DATABASE_ID")
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
def cli(notion_db_id: str, model: str, api_base: str, log_level: str):
    """Main CLI entry point for the YouTube summarizer.

    Retrieves videos from a Notion database, extracts transcripts and metadata,
    generates summaries and key points using an LLM, and updates the database
    with the results.

    Args:
        notion_db_id: The Notion database ID containing videos to process.
            Can be provided as --notion-db-id flag or NOTION_DATABASE_ID env var.
        model: The LLM model identifier (default: ollama/llama3.2).
            Can be set via LLM_MODEL environment variable.
        api_base: The LLM API base URL (default: http://localhost:11434).
            Can be set via LLM_API_BASE environment variable.
        log_level: The logging level (default: INFO).
            Can be DEBUG, INFO, WARNING, ERROR, or CRITICAL.

    Raises:
        KeyError: If NOTION_TOKEN environment variable is not set.
    """
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.debug(f"Starting YouTube summarizer with log level: {log_level}")
    logger.info(f"Using model: {model}")
    logger.info(f"Using API base: {api_base}")

    service = YouTubeSummarizerService(
        token=os.environ["NOTION_TOKEN"], model=model, api_base=api_base
    )
    logger.info("Initialized YouTube summarizer service")

    for video in service.get_videos(notion_db_id):
        logger.debug(f"Processing video: {video}")
        service.update_video(notion_db_id, video)

    logger.info("YouTube summarizer completed successfully")
