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
        logger.info(f"Retrieving videos from Notion database: {notion_db_id}")
        properties = self.notion_client.get_page_properties_from_database(notion_db_id)
        logger.debug(f"Retrieved {len(properties)} records from database")
        videos = []
        for i, prop in enumerate(properties, 1):
            # Skip records without YouTube URLs
            if not prop.get("URL"):
                logger.debug(f"Skipping record {i}: No YouTube URL found")
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
            logger.debug(f"Processing video {i}: {video.url}")
            yt_client = YouTubeClient(video.url)

            # Fetch missing metadata from YouTube
            if not video.title:
                logger.debug(f"Fetching missing metadata for video {i}")
                if not video.title:
                    logger.debug(f"Fetching title for video {i}")
                    video.title = yt_client.get_video_title()
                    video.updated = True

            # Generate summary if not already present
            transcript = None
            if not video.summary:
                logger.info(f"Generating summary for video {i}")
                transcript = yt_client.get_video_transcript()
                video.summary = self.llm_client.summarize(transcript)
                video.updated = True

            # Extract main points if not already present
            if not video.main_points:
                logger.info(f"Extracting main points for video {i}")
                # Fetch transcript if we didn't already fetch it for summary
                if transcript is None:
                    transcript = yt_client.get_video_transcript()
                video.main_points = self.llm_client.get_main_points(transcript)
                video.updated = True

            videos.append(video)
            logger.debug(f"Completed processing video {i}")

        logger.info(f"Successfully processed {len(videos)} videos")
        return videos

    def update_video(self, notion_db_id: str, video: YouTubeVideo):
        """Update a video record in the Notion database with processed content.

        Persists the video's title, summary, and main points back to the Notion
        database by updating the corresponding page with the generated content.

        Args:
            notion_db_id: The Notion database ID containing the video record.
            video: The YouTubeVideo object with updated content to persist.
        """
        logger.debug(f"Updating video record in database: {video.id}")
        properties = {
            "Title": video.title,
            "Summary": video.summary,
            "Main Points": video.main_points,
        }
        self.notion_client.update_page_properties(notion_db_id, video.id, properties)
        logger.debug(f"Successfully updated video record: {video.id}")
