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

"""YouTube video data extraction module.

Provides functionality to extract metadata and transcripts from YouTube videos
using URLs. Handles video ID parsing, title extraction via HTML parsing, and
transcript retrieval using the YouTube Transcript API.
"""

import logging
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)


class Client:
    """Client for extracting data from YouTube videos.

    Provides methods to retrieve video metadata (title) and complete transcripts
    from YouTube videos by parsing the video URL and using official APIs.
    """

    def __init__(self, url: str):
        """Initialize YouTube client with a video URL.

        Args:
            url: Full YouTube video URL (e.g., https://www.youtube.com/watch?v=VIDEO_ID)

        Raises:
            KeyError: If the URL does not contain a valid 'v' query parameter.
        """
        self.url = url
        query = urlparse(url).query
        self.video_id = parse_qs(query)["v"][0]
        logger.debug(f"Initialized YouTube client for video ID: {self.video_id}")

    def get_video_transcript(self) -> str:
        """Retrieve the complete transcript of the YouTube video.

        Fetches the transcript from YouTube's transcript API and joins all
        snippets into a single continuous text.

        Returns:
            A string containing the complete video transcript with all snippets
            joined by spaces.

        Raises:
            Exception: If transcript is unavailable or API call fails.
        """
        logger.info(f"Fetching transcript for video ID: {self.video_id}")
        try:
            transcript = YouTubeTranscriptApi().fetch(self.video_id)
            transcript_text = " ".join(
                [snippet.text for snippet in transcript.snippets]
            )
            logger.debug(
                f"Successfully retrieved transcript with {len(transcript.snippets)} snippets"
            )
            return transcript_text
        except Exception as e:
            logger.error(
                f"Failed to fetch transcript for video ID {self.video_id}: {e}"
            )
            raise

    def get_video_title(self) -> str:
        """Extract the video title from the YouTube page.

        Parses the video page HTML and extracts the title from the Open Graph
        meta tag (og:title), which is the canonical page title.

        Returns:
            The video title as a string, or "Title not found" if extraction fails.
        """
        logger.info(f"Fetching title for video ID: {self.video_id}")
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            html_content = response.text
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract title from Open Graph meta tag for reliable results
            title_tag = soup.find("meta", property="og:title")
            title = title_tag["content"] if title_tag else "Title not found"
            logger.debug(f"Successfully retrieved title: {title}")
            return title
        except Exception as e:
            logger.error(f"Failed to fetch title for video ID {self.video_id}: {e}")
            return "Title not found"
