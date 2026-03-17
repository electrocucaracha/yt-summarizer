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
from typing import Optional

import httpx
import yt_dlp
from youtube_transcript_api.proxies import WebshareProxyConfig

from .llm import Client as LLMClient
from .model import YouTubeVideo
from .notion import Client as NotionClient
from .youtube import Client as YouTubeClient

logger = logging.getLogger(__name__)


class YouTubeSummarizerService:
    """Service for processing and summarizing YouTube videos.

    Orchestrates the complete workflow: retrieving video references from Notion,
    extracting video metadata and transcripts from YouTube, generating summaries
    and key points using an LLM, and persisting results back to Notion.
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        token: str,
        notion_db_id: str,
        model: str = "ollama/llama3.2",
        api_base: str = "http://localhost:11434",
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
    ):
        """Initialize the summarizer service with database and LLM clients.

        Args:
            token: Notion API authentication token.
            notion_db_id: The Notion database ID containing video records.
            model: LLM model identifier (default: ollama/llama3.2).
            api_base: LLM API base URL (default: http://localhost:11434).
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

        logger.debug("Initializing NotionClient with token: %s", token)
        self.notion_client = NotionClient(token=token, client=http_client_proxy)
        self.llm_client = LLMClient(model=model, api_base=api_base)
        logger.debug("Service initialized successfully")

    def get_videos_from_notion_db(self):
        """Retrieve and process all videos from a Notion database.

        Fetches all video records from the Notion database, extracts any missing
        metadata and transcripts from YouTube, and generates summaries and key
        points using the LLM if not already present.

        Returns:
            A list of YouTubeVideo objects with complete metadata, transcripts,
            summaries, and main points populated.

        Processing flow:
            1. Retrieve all database records
            2. For each record with a URL:
               - Extract YouTube video ID and create YouTubeVideo object
               - Fetch title from YouTube if missing
               - Fetch transcript from YouTube if missing
               - Generate summary via LLM if missing
               - Extract main points via LLM if missing
        """
        logger.info("Retrieving videos from Notion database: %s", self.notion_db_id)
        properties = self.notion_client.get_page_properties_from_database(
            self.notion_db_id
        )
        logger.debug("Retrieved %d records from database", len(properties))
        result = []
        valid_count = 0
        invalid_count = 0

        for i, prop in enumerate(properties, 1):
            # Skip records without YouTube URLs
            if not prop.get("URL"):
                logger.debug("Skipping record %d: No YouTube URL found", i)
                invalid_count += 1
                continue

            valid_count += 1
            # Ensure the URL is extracted correctly from rich text
            url = prop["URL"]
            if isinstance(url, list) and url:
                first_item = url[0]
                if isinstance(first_item, dict) and "text" in first_item:
                    logger.debug("Extracting URL from rich text object: %s", first_item)
                    url = first_item["text"].get("content", "")
                else:
                    logger.warning("Unexpected structure in URL list: %s", url)
                    url = ""
            elif not isinstance(url, str):
                logger.warning("Unexpected URL type: %s", type(url))
                url = ""
            logger.debug("Processing record %d with URL: %s", i, url)
            video = YouTubeVideo(
                id=prop.get("ID", ""),
                url=url,
                title=prop.get("Title", None),
                transcript=prop.get("Transcript", None),
                summary=prop.get("Summary", None),
                main_points=prop.get("Main points", None),
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

    def _process_video(self, video: YouTubeVideo) -> YouTubeVideo:
        """Process an individual video to populate missing metadata and summaries.

        For a given YouTubeVideo object, this method checks for missing title,
        transcript, summary, and main points. It retrieves any missing information
        from YouTube and generates summaries and key points using the LLM as needed.

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
        if not result.title:
            logger.debug("Fetching missing metadata for video: %s", result.url)
            if not result.title:
                logger.debug("Fetching title for video: %s", result.url)
                result.title = self.youtube_client.get_video_title(url=result.url)

        # Generate summary if not already present
        transcript = None
        if not result.summary:
            logger.info("Generating summary for video: %s", result.url)
            transcript = self.youtube_client.get_video_transcript(url=result.url)
            result.summary = self.llm_client.summarize(transcript)

        # Extract main points if not already present
        if not result.main_points:
            logger.info("Extracting main points for video: %s", result.url)
            # Fetch transcript if we didn't already fetch it for summary
            if transcript is None:
                transcript = self.youtube_client.get_video_transcript(url=result.url)
            result.main_points = self.llm_client.get_main_points(transcript)

        return result

    def upsert_video(self, video: YouTubeVideo):
        """Upsert a video's metadata in the Notion database.

        Args:
            video: A YouTubeVideo object with updated metadata.
        """
        # Compute the hash before processing
        original_hash = video.compute_hash()

        # Process the video
        updated_video = self._process_video(video)

        # Compute the hash after processing
        updated_hash = updated_video.compute_hash()

        # Check if the video has changed
        if original_hash != updated_hash:
            logger.info("Video has changed. Updating Notion database.")
            # Proceed with upsert logic
            properties = {
                "Title": updated_video.title,
                "URL": updated_video.url,
                "Summary": updated_video.summary,
                "Main Points": updated_video.main_points,
            }
            try:
                if updated_video.id:
                    logger.debug("Updating existing page with ID: %s", updated_video.id)
                    self.notion_client.update_page_properties(
                        self.notion_db_id,
                        updated_video.id,
                        properties=properties,
                    )
                else:
                    logger.debug(
                        "Creating a new page in database: %s", self.notion_db_id
                    )
                    updated_video.id = self.notion_client.create_page(
                        self.notion_db_id,
                        properties=properties,
                    )
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Failed to update or create video in Notion: %s", e)
        else:
            logger.info("No changes detected for video: %s", video.url)

    def get_videos_from_playlist(self, playlist_url: str):
        """Extract video metadata from a YouTube playlist URL.

        Args:
            playlist_url: The URL of the YouTube playlist to extract videos from.
        Returns:
            A list of YouTubeVideo objects containing metadata for each video in the playlist.
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

        return result
