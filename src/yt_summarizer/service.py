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
complete pipeline for summarizing videos.
"""

import logging

import yt_dlp

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

    def __init__(
        self,
        token: str,
        model: str = "ollama/llama3.2",
        api_base: str = "http://localhost:11434",
    ):
        """Initialize the summarizer service with database and LLM clients.

        Args:
            token: Notion API authentication token.
            model: LLM model identifier (default: ollama/llama3.2).
            api_base: LLM API base URL (default: http://localhost:11434).
        """
        logger.debug("Initializing YouTube summarizer service")
        self.notion_client = NotionClient(token=token)
        self.llm_client = LLMClient(model=model, api_base=api_base)
        logger.debug("Service initialized successfully")

    def get_videos(self, notion_db_id: str):
        """Retrieve and process all videos from a Notion database.

        Fetches all video records from the Notion database, extracts any missing
        metadata and transcripts from YouTube, and generates summaries and key
        points using the LLM if not already present.

        Args:
            notion_db_id: The Notion database ID containing video records.

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
        logger.info("Retrieving videos from Notion database: %s", notion_db_id)
        properties = self.notion_client.get_page_properties_from_database(notion_db_id)
        logger.debug("Retrieved %d records from database", len(properties))
        videos = []
        for i, prop in enumerate(properties, 1):
            # Skip records without YouTube URLs
            if not prop.get("URL"):
                logger.debug("Skipping record %d: No YouTube URL found", i)
                continue

            # Create video object with existing data from Notion
            video = YouTubeVideo(
                id=prop.get("ID", ""),
                url=prop["URL"],
                title=prop.get("Title", None),
                transcript=prop.get("Transcript", None),
                summary=prop.get("Summary", None),
                main_points=prop.get("Main points", None),
            )
            self._process_video(video)
            videos.append(video)

        logger.info("Successfully processed %d videos", len(videos))
        return videos

    def _process_video(self, video: YouTubeVideo):
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
        yt_client = YouTubeClient(video.url)

        # Fetch missing metadata from YouTube
        if not video.title:
            logger.debug("Fetching missing metadata for video: %s", video.url)
            if not video.title:
                logger.debug("Fetching title for video: %s", video.url)
                video.title = yt_client.get_video_title()
                video.updated = True

        # Generate summary if not already present
        transcript = None
        if not video.summary:
            logger.info("Generating summary for video: %s", video.url)
            transcript = yt_client.get_video_transcript()
            video.summary = self.llm_client.summarize(transcript)
            video.updated = True

        # Extract main points if not already present
        if not video.main_points:
            logger.info("Extracting main points for video: %s", video.url)
            # Fetch transcript if we didn't already fetch it for summary
            if transcript is None:
                transcript = yt_client.get_video_transcript()
            video.main_points = self.llm_client.get_main_points(transcript)
            video.updated = True

        logger.debug("Completed processing video: %s", video.url)
        return video

    def update_video(self, notion_db_id: str, video: YouTubeVideo):
        """Update a video record in the Notion database with processed content.

        Persists the video's title, summary, and main points back to the Notion
        database by updating the corresponding page with the generated content.

        Args:
            notion_db_id: The Notion database ID containing the video record.
            video: The YouTubeVideo object with updated content to persist.
        """
        logger.debug("Updating video record in database: %s", video.id)
        properties = {
            "Title": video.title,
            "Summary": video.summary,
            "Main Points": video.main_points,
        }
        self.notion_client.update_page_properties(notion_db_id, video.id, properties)
        logger.debug("Successfully updated video record: %s", video.id)

    def create_video(self, notion_db_id: str, video: YouTubeVideo):
        """Create a new video record in the Notion database.

        Persists a video's metadata into the Notion database as a new page.

        Args:
            notion_db_id: The Notion database ID where the record will be created.
            video: The YouTubeVideo object containing data to persist.
        """
        logger.debug("Creating video record in database for video: %s", video.title)

        properties = {
            "Title": video.title,
            "URL": video.url,
            "Summary": video.summary,
            "Main Points": video.main_points,
        }

        page_id = self.notion_client.create_page(notion_db_id, properties)

        if page_id:
            video.id = page_id
            logger.debug("Successfully created video record: %s", page_id)
        else:
            logger.error("Failed to create video record for video: %s", video.title)

    def process_playlist(self, playlist_url: str, notion_db_id: str):
        """Process a YouTube playlist and update the Notion database with video summaries."""
        logger.info("Processing playlist: %s", playlist_url)

        ydl_opts = {
            "extract_flat": True,
            "quiet": True,
        }

        logger.debug("Initializing YoutubeDL with options: %s", ydl_opts)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.debug("Calling extract_info with playlist_url: %s", playlist_url)
            info = ydl.extract_info(playlist_url, download=False)
            logger.debug("Extracted info: %s", info)

            processed_count = 0
            for entry in info["entries"]:
                logger.debug("Processing entry: %s", entry)
                video = YouTubeVideo(
                    id=entry["id"],
                    url=f"https://www.youtube.com/watch?v={entry['id']}",
                    title=entry.get("title"),
                )
                video.updated = True
                self._process_video(video)
                self.create_video(notion_db_id, video)
                processed_count += 1

            logger.info("Completed processing playlist: %s", playlist_url)
            logger.info("Total videos processed: %d", processed_count)
