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

"""Main service orchestrating video processing workflow.

Defines the YouTubeSummarizerService class which coordinates interactions between
the Notion database, YouTube data extraction, and LLM processing to create a
complete pipeline for summarizing videos. This service ensures seamless integration
of all components for efficient video summarization.
"""

import copy
import logging

import click
import httpx
import yt_dlp
from youtube_transcript_api.proxies import WebshareProxyConfig

from .llm import EXECUTIVE_SUMMARY_CHAR_LIMIT
from .llm import Client as LLMClient
from .model import YouTubeVideo
from .notion import Client as NotionClient
from .okf import Client as OKFClient
from .youtube import Client as YouTubeClient

logger = logging.getLogger(__name__)
PLAYLIST_SUMMARY_CHUNK_SIZE = 25


class YouTubeSummarizerService:
    """Service for processing and summarizing YouTube videos.

    Orchestrates the complete workflow: retrieving video references from Notion,
    extracting video metadata and transcripts from YouTube, generating summaries
    and key points using an LLM, and persisting results back to Notion.
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        token: str | None = None,
        notion_db_id: str | None = None,
        model: str = "ollama/llama3.2",
        api_base: str | None = None,
        proxy_username: str | None = None,
        proxy_password: str | None = None,
        output_dir: str | None = None,
    ):
        """Initialize the summarizer service with storage and LLM clients.

        At least one storage backend must be configured: Notion (``token`` plus
        ``notion_db_id``) or the filesystem (``output_dir``).

        Args:
            token: Notion API authentication token. Optional.
            notion_db_id: The Notion database ID containing video records. Optional.
            model: LLM model identifier (default: ollama/llama3.2).
            api_base: Optional LLM API base URL. Defaults to None (use provider default).
            proxy_username: Optional Webshare proxy username.
            proxy_password: Optional Webshare proxy password.
            output_dir: Optional root folder of the OKF bundle to write.

        Raises:
            ValueError: If no storage backend is configured.
        """
        logger.debug("Initializing YouTube summarizer service")

        self.notion_db_id = notion_db_id
        self.youtube_client = YouTubeClient()
        http_client_proxy = httpx.Client()  # Default client without proxy
        if proxy_username and proxy_password:
            self.proxy_config = WebshareProxyConfig(
                proxy_username=proxy_username, proxy_password=proxy_password
            )
            self.youtube_client = YouTubeClient(
                proxy_username=proxy_username, proxy_password=proxy_password
            )
            http_client_proxy = httpx.Client(proxy=self.proxy_config.url)

        self.notion_client = None
        if token and notion_db_id:
            logger.debug("Initializing NotionClient for database: %s", notion_db_id)
            self.notion_client = NotionClient(token=token, client=http_client_proxy)

        self.okf_client = OKFClient(root=output_dir) if output_dir else None

        if not self.notion_client and not self.okf_client:
            raise ValueError(
                "No storage backend configured: provide Notion credentials or an "
                "output directory."
            )

        self.llm_client = LLMClient(model=model, api_base=api_base)
        logger.debug("Service initialized successfully")

    def get_videos_from_notion_db(self):
        """Retrieve video records from Notion and normalize them into models.

        This method does not enrich records with YouTube or LLM data. It only
        reads page properties from Notion, normalizes the stored URL field, and
        returns lightweight ``YouTubeVideo`` objects for later processing.

        Returns:
            A list of ``YouTubeVideo`` objects for records that contain a URL.
            Empty when Notion is not configured.
        """
        if not self.notion_client:
            logger.info("Notion is not configured; skipping database retrieval")
            return []

        logger.info("Retrieving videos from Notion database: %s", self.notion_db_id)
        properties = self.notion_client.get_page_properties_from_database(
            self.notion_db_id
        )
        logger.debug("Retrieved %d records from database", len(properties))
        result = []
        valid_count = 0
        invalid_count = 0

        for i, prop in enumerate(properties, 1):
            url = self._normalize_notion_text(prop.get("URL"))
            # Skip records without YouTube URLs
            if not url:
                logger.debug("Skipping record %d: No YouTube URL found", i)
                invalid_count += 1
                click.echo(f"Record {i} skipped: No YouTube URL found.")
                continue

            valid_count += 1
            logger.debug("Processing record %d with URL: %s", i, url)
            video = YouTubeVideo(
                id=prop.get("ID", ""),
                url=url,
                title=self._normalize_notion_text(prop.get("Title")),
                transcript=self._normalize_notion_text(prop.get("Transcript")),
                summary=self._normalize_notion_text(prop.get("Summary")),
                main_points=self._normalize_notion_text(
                    prop.get("Main points") or prop.get("Main Points")
                ),
            )
            result.append(video)
            logger.debug("Added video: %s", video)

        logger.info(
            "Processed %d valid records and skipped %d invalid records",
            valid_count,
            invalid_count,
        )
        logger.info("Successfully processed %d videos", len(result))
        logger.debug("Final videos list: %s", result)
        return result

    def _normalize_notion_text(self, value) -> str:
        """Convert Notion property payloads into plain strings."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            parts = []
            for item in value:
                if not isinstance(item, dict):
                    continue
                plain_text = item.get("plain_text")
                if plain_text:
                    parts.append(str(plain_text))
                    continue
                text = item.get("text", {})
                content = text.get("content") if isinstance(text, dict) else None
                if content:
                    parts.append(str(content))
            return "".join(parts).strip()
        return str(value).strip()

    def _fetch_with_retries(self, fetch_function, *args, retries=3, **kwargs):
        """Retry a function up to `retries` times before giving up."""
        for attempt in range(1, retries + 1):
            try:
                return fetch_function(*args, **kwargs)
            except (OSError, TypeError, ValueError, httpx.HTTPError) as e:
                logger.warning("Attempt %d/%d failed: %s", attempt, retries, str(e))
                if attempt == retries:
                    logger.error("All retry attempts failed.")
                    return None
        return None

    def _process_video(self, video: YouTubeVideo) -> YouTubeVideo:
        """Populate missing title, summary, and main points for one video.

        The original ``video`` instance is deep-copied before enrichment. The
        transcript is fetched only when needed for summary or main-point
        generation and is not stored back on the returned object.

        Args:
            video: A YouTubeVideo object with potentially incomplete data.

        Returns:
            The updated YouTubeVideo object with all fields populated.
        """
        logger.debug("Processing video: %s", video.url)
        result = copy.deepcopy(
            video
        )  # Create a copy to avoid mutating the original object

        # Fetch missing metadata from YouTube
        if not result.title or result.title == "Title not found":
            logger.debug("Fetching missing metadata for video: %s", result.url)
            result.title = self.youtube_client.get_video_title(url=result.url)

        transcript = None
        needs_transcript = not result.summary or not result.main_points
        if needs_transcript:
            transcript = self._fetch_with_retries(
                self.youtube_client.get_video_transcript, url=result.url
            )
            if not transcript:
                logger.warning(
                    "Skipping video due to transcript fetch failure: %s", result.url
                )
            else:
                if not result.summary:
                    logger.info("Generating summary for video: %s", result.url)
                    result.summary = self.llm_client.summarize(transcript)
                if not result.main_points:
                    logger.info("Extracting main points for video: %s", result.url)
                    result.main_points = self.llm_client.get_main_points(transcript)

        return result

    def get_videos_from_filesystem(self, playlist_title: str | None = None):
        """Load already summarized videos from the OKF bundle on disk.

        Args:
            playlist_title: Playlist whose concepts should be loaded.

        Returns:
            A list of ``YouTubeVideo`` objects, or an empty list when the
            filesystem backend is not configured.
        """
        if not self.okf_client:
            logger.info("Filesystem storage is not configured; skipping retrieval")
            return []
        return self.okf_client.get_videos(playlist_title)

    def upsert_video(
        self, video: YouTubeVideo, playlist_title: str | None = None
    ) -> YouTubeVideo:
        """Persist a video in every configured backend when its content changed.

        The method enriches the supplied video, compares the before/after content
        hash, and only writes ``Title``, ``URL``, ``Summary``, and
        ``Main Points`` when the persisted fields changed.

        Args:
            video: A YouTubeVideo object with updated metadata.
            playlist_title: Playlist used to place the OKF concept document.
        """
        # Compute the hash before processing
        original_hash = video.compute_hash()

        # Process the video
        updated_video = self._process_video(video)

        # Compute the hash after processing
        updated_hash = updated_video.compute_hash()

        # Check if the video has changed
        if original_hash != updated_hash:
            logger.info("Video has changed. Updating configured storage backends.")
            self._upsert_video_in_notion(updated_video)
            self._upsert_video_in_filesystem(updated_video, playlist_title)
        else:
            logger.info("No changes detected for video: %s", video.url)

        return updated_video

    def _upsert_video_in_notion(self, video: YouTubeVideo) -> None:
        """Create or update the Notion row backing ``video``."""
        if not self.notion_client or not self.notion_db_id:
            return

        notion_db_id = self.notion_db_id
        properties = {
            "Title": video.title,
            "URL": video.url,
            "Summary": video.summary,
            "Main Points": video.main_points,
        }
        try:
            if video.id:
                logger.debug("Updating existing page with ID: %s", video.id)
                self.notion_client.update_page_properties(
                    notion_db_id,
                    video.id,
                    properties=properties,
                )
            else:
                logger.debug("Creating a new page in database: %s", self.notion_db_id)
                video.id = self.notion_client.create_page(
                    notion_db_id,
                    properties=properties,
                )
        except (OSError, TypeError, ValueError, httpx.HTTPError) as e:
            logger.error("Failed to update or create video in Notion: %s", e)

    def _upsert_video_in_filesystem(
        self, video: YouTubeVideo, playlist_title: str | None
    ) -> None:
        """Write the OKF concept document backing ``video``."""
        if not self.okf_client:
            return

        try:
            self.okf_client.write_video(video, playlist_title=playlist_title)
        except OSError as e:
            logger.error("Failed to write video concept to the filesystem: %s", e)

    def store_playlist(
        self,
        videos: list[YouTubeVideo],
        playlist_title: str | None = None,
        playlist_summary: str = "",
        playlist_url: str | None = None,
    ) -> None:
        """Write the playlist concept and index files to the OKF bundle.

        No-op when the filesystem backend is not configured.
        """
        if not self.okf_client:
            return

        try:
            self.okf_client.write_playlist(
                videos,
                playlist_title=playlist_title,
                playlist_summary=playlist_summary,
                playlist_url=playlist_url,
            )
        except OSError as e:
            logger.error("Failed to write playlist bundle to the filesystem: %s", e)

    def get_videos_from_playlist(self, playlist_url: str):
        """Extract playlist title and flat video metadata from a playlist URL.

        Args:
            playlist_url: The URL of the YouTube playlist to extract videos from.

        Returns:
            A dictionary with the playlist ``title`` and a ``videos`` list of
            ``YouTubeVideo`` objects populated with URLs and titles.
        """

        logger.info("Processing playlist: %s", playlist_url)

        ydl_opts = {
            "extract_flat": True,
            "quiet": True,
        }

        logger.debug("Initializing YoutubeDL with options: %s", ydl_opts)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.debug("Calling extract_info with playlist_url: %s", playlist_url)
                info = ydl.extract_info(playlist_url, download=False)
                logger.debug("Extracted info: %s", info)
        except yt_dlp.utils.DownloadError as e:
            logger.error("Failed to process playlist due to download error: %s", str(e))
            raise
        except Exception as e:
            logger.error("An unexpected error occurred: %s", str(e))
            raise

        result = []
        for entry in info["entries"]:
            url = f"https://www.youtube.com/watch?v={entry['id']}"
            video = YouTubeVideo(
                url=url,
                title=entry.get("title"),
            )

            result.append(video)

        return {"title": info.get("title", "Untitled Playlist"), "videos": result}

    def _chunk_summaries(
        self, summaries: list[str], chunk_size: int
    ) -> list[list[str]]:
        """Split summaries into fixed-size chunks for hierarchical reduction.

        Examples:
            >>> service = object.__new__(YouTubeSummarizerService)
            >>> service._chunk_summaries(["one", "two", "three"], 2)
            [['one', 'two'], ['three']]
        """
        return [
            summaries[index : index + chunk_size]
            for index in range(0, len(summaries), chunk_size)
        ]

    def _reduce_playlist_summaries(
        self, summaries: list[str], playlist_title: str | None = None
    ) -> str:
        """Reduce many summaries into one by iterating over fixed-size chunks.

        Blank summaries are removed before reduction. Each chunk is summarized
        with playlist context, then the intermediate summaries are reduced again
        until only one summary remains.
        """
        current_summaries = [
            summary.strip() for summary in summaries if summary.strip()
        ]
        reduction_level = 1

        while len(current_summaries) > 1:
            logger.info(
                "Reducing playlist summaries at level %d with %d inputs",
                reduction_level,
                len(current_summaries),
            )
            next_level = []
            summary_chunks = self._chunk_summaries(
                current_summaries, PLAYLIST_SUMMARY_CHUNK_SIZE
            )
            for chunk_index, chunk in enumerate(summary_chunks, 1):
                logger.debug(
                    "Summarizing playlist chunk %d at level %d with %d summaries",
                    chunk_index,
                    reduction_level,
                    len(chunk),
                )
                reduced_summary = self.llm_client.generate_executive_summary(
                    "\n\n".join(chunk), playlist_title=playlist_title
                ).strip()
                if reduced_summary:
                    next_level.append(reduced_summary)

            current_summaries = next_level
            reduction_level += 1

        return current_summaries[0] if current_summaries else ""

    def generate_playlist_summary(
        self, videos: list[YouTubeVideo], playlist_title: str | None = None
    ) -> str:
        """Generate an executive summary from the summaries attached to videos.

        Args:
            videos: List of ``YouTubeVideo`` objects. Only truthy ``summary``
                values are used.
            playlist_title: Optional playlist title to use as summary context.

        Returns:
            A single executive summary string limited to
            ``EXECUTIVE_SUMMARY_CHAR_LIMIT`` characters.
        """
        logger.info("Generating executive summary for playlist")

        summaries = [
            str(video.summary).strip()
            for video in videos
            if hasattr(video, "summary") and video.summary
        ]
        logger.debug("Collected normalized summaries from videos: %s", summaries)

        summaries = [summary for summary in summaries if summary]
        logger.debug("Filtered non-empty summaries: %s", summaries)

        if not summaries:
            logger.info("No video summaries available to generate a playlist summary")
            return ""

        if len(summaries) == 1:
            combined_summary = self.llm_client.generate_executive_summary(
                summaries[0], playlist_title=playlist_title
            )
        else:
            combined_summary = self._reduce_playlist_summaries(
                summaries, playlist_title=playlist_title
            )

        if len(combined_summary) > EXECUTIVE_SUMMARY_CHAR_LIMIT:
            combined_summary = (
                combined_summary[: EXECUTIVE_SUMMARY_CHAR_LIMIT - 3] + "..."
            )

        logger.info("Generated executive summary: %s", combined_summary)
        return combined_summary
