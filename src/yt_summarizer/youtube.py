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
transcript retrieval using the YouTube Transcript API. This module ensures
robust handling of various YouTube video formats and restrictions.
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
        self.proxy_config = None
        if proxy_username and proxy_password:
            logger.debug("Using proxy authentication for transcript retrieval")
            self.proxy_config = WebshareProxyConfig(
                proxy_username=proxy_username, proxy_password=proxy_password
            )
            self.ytt_api = YouTubeTranscriptApi(proxy_config=self.proxy_config)

    def get_video_transcript(  # pylint: disable=too-many-return-statements
        self, url: str
    ) -> str:
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

            # Log the raw transcript structure for debugging
            logger.debug("Raw transcript structure: %s", transcript)

            # Handle FetchedTranscript type
            if hasattr(transcript, "snippets"):
                try:
                    transcript_text = " ".join(
                        snippet.text for snippet in transcript.snippets
                    )
                    logger.debug(
                        "Successfully processed FetchedTranscript with %d snippets",
                        len(transcript.snippets),
                    )
                    return transcript_text
                except AttributeError as e:
                    logger.error(
                        "FetchedTranscript object is missing expected attributes: %s", e
                    )

            # Validate the structure of the transcript object
            elif isinstance(transcript, list):
                if all(
                    isinstance(snippet, dict) and "text" in snippet
                    for snippet in transcript
                ):
                    transcript_text = " ".join(
                        snippet["text"] for snippet in transcript
                    )
                    logger.debug(
                        "Successfully retrieved transcript with %d snippets",
                        len(transcript),
                    )
                    return transcript_text
                logger.error(
                    "Transcript list contains invalid snippet structures: %s",
                    [
                        snippet
                        for snippet in transcript
                        if not isinstance(snippet, dict) or "text" not in snippet
                    ],
                )
            else:
                logger.error(
                    "Unexpected transcript structure type: %s", type(transcript)
                )
                raise SystemExit("Critical error: Unexpected transcript structure.")

            return ""
        except AgeRestricted:
            logger.warning("Video is age-restricted and cannot fetch transcript.")
            return ""
        except NoTranscriptFound:
            logger.warning("No transcript found for video ID: %s", video_id)
            return ""
        except TranscriptsDisabled:
            logger.warning("Transcripts are disabled for video ID: %s", video_id)
            return ""
        except VideoUnavailable:
            logger.warning("Video is unavailable or deleted: %s", video_id)
            return ""
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Failed to fetch transcript for video ID %s: %s", video_id, e)
            return ""

    def get_video_title(self, url: str) -> str:
        """Extract the video title from the YouTube page.

        Parses the video page HTML and extracts the title from the Open Graph
        meta tag (og:title), which is the canonical page title.

        Returns:
            The video title as a string, or "Title not found" if extraction fails.
        """
        logger.info("Fetching title for video URL: %s", url)
        try:
            if self.proxy_config:
                logger.debug("Using proxy configuration for title retrieval")
                response = requests.get(
                    url, proxies=self.proxy_config.to_requests_dict(), timeout=30
                )
            else:
                response = requests.get(url, timeout=30)
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
            logger.error("Failed to fetch title for video URL %s: %s", url, e)
            return "Title not found"
