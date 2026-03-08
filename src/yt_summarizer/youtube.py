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
from youtube_transcript_api._errors import (
    AgeRestricted,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)
from youtube_transcript_api.proxies import WebshareProxyConfig

logger = logging.getLogger(__name__)


class Client:
    """Client for extracting data from YouTube videos.

    Provides methods to retrieve video metadata (title) and complete transcripts
    from YouTube videos by parsing the video URL and using official APIs.
    """

    def __init__(self, proxy_username: str = None, proxy_password: str = None):
        """Initialize YouTube client with a video URL.

        Args:
            url: Full YouTube video URL (e.g., https://www.youtube.com/watch?v=VIDEO_ID)
            proxy_username: Optional proxy username for YouTube client.
            proxy_password: Optional proxy password for YouTube client.

        Raises:
            KeyError: If the URL does not contain a valid 'v' query parameter.
        """
        self.ytt_api = YouTubeTranscriptApi()
        if proxy_username and proxy_password:
            logger.debug("Using proxy authentication for transcript retrieval")
            self.proxy_config = WebshareProxyConfig(
                proxy_username=proxy_username, proxy_password=proxy_password
            )
            self.ytt_api = YouTubeTranscriptApi(proxy_config=self.proxy_config)

    def get_video_transcript(self, url: str) -> str:
        """Retrieve the complete transcript of the YouTube video.

        Fetches the transcript from YouTube's transcript API and joins all
        snippets into a single continuous text.

        Returns:
            A string containing the complete video transcript with all snippets
            joined by spaces.

        Raises:
            AgeRestricted: If video is age-restricted and requires authentication.
            NoTranscriptFound: If no transcript is available for the video.
            TranscriptsDisabled: If transcripts are disabled for the video.
            VideoUnavailable: If the video is unavailable or deleted.
            Exception: For other API call failures.
        """

        query = urlparse(url).query
        video_id = parse_qs(query)["v"][0]

        logger.info("Fetching transcript for video ID: %s", video_id)

        try:
            transcript = self.ytt_api.fetch(video_id)
            transcript_text = " ".join(
                [snippet.text for snippet in transcript.snippets]
            )
            logger.debug(
                "Successfully retrieved transcript with %d snippets",
                len(transcript.snippets),
            )
            return transcript_text
        except AgeRestricted:
            logger.warning(
                "Video %s is age-restricted and requires authentication. "
                "Cookie-based authentication is currently not supported by the "
                "youtube-transcript-api library. Video cannot be processed.",
                video_id,
            )
            raise
        except NoTranscriptFound:
            logger.error(
                "No transcript found for video ID %s. The video may not have "
                "captions/subtitles available.",
                video_id,
            )
            raise
        except TranscriptsDisabled:
            logger.error(
                "Transcripts are disabled for video ID %s. The video owner has "
                "disabled captions/subtitles.",
                video_id,
            )
            raise
        except VideoUnavailable:
            logger.error(
                "Video %s is unavailable. It may have been deleted or made private.",
                video_id,
            )
            raise
        except Exception as e:
            logger.error("Failed to fetch transcript for video ID %s: %s", video_id, e)
            raise

    def get_video_title(self, url: str) -> str:
        """Extract the video title from the YouTube page.

        Parses the video page HTML and extracts the title from the Open Graph
        meta tag (og:title), which is the canonical page title.

        Returns:
            The video title as a string, or "Title not found" if extraction fails.
        """
        logger.info("Fetching title for video ID: %s", self.video_id)
        try:
            if self.proxy_config:
                logger.debug("Using proxy configuration for title retrieval")
                response = requests.get(
                    url, proxies=self.proxy_config.to_requests_dict()
                )
            else:
                response = requests.get(url)
            response.raise_for_status()
            html_content = response.text
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract title from Open Graph meta tag for reliable results
            title_tag = soup.find("meta", property="og:title")
            title = title_tag["content"] if title_tag else "Title not found"
            logger.debug("Successfully retrieved title: %s", title)
            return title
        except (
            requests.exceptions.RequestException,
            requests.exceptions.HTTPError,
        ) as e:
            logger.error("Failed to fetch title for video ID %s: %s", self.video_id, e)
            return "Title not found"
