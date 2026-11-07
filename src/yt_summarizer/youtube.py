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
import time
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    AgeRestricted,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
)
from youtube_transcript_api.proxies import WebshareProxyConfig

logger = logging.getLogger(__name__)
DEFAULT_LANGUAGE = "en"
# Languages tried after the requested one; the LLM translates the result.
FALLBACK_TRANSCRIPT_LANGUAGES = ("en", "en-US", "en-GB", "es", "es-419")


def transcript_languages(language: str = DEFAULT_LANGUAGE) -> tuple[str, ...]:
    """Return transcript languages in priority order, requested one first."""
    return tuple(dict.fromkeys((language, *FALLBACK_TRANSCRIPT_LANGUAGES)))


class Client:
    """Client for extracting data from YouTube videos.

    Provides methods to retrieve video metadata (title) and complete transcripts
    from YouTube videos by parsing the video URL and using official APIs.
    """

    def __init__(
        self,
        proxy_username: str | None = None,
        proxy_password: str | None = None,
        language: str = DEFAULT_LANGUAGE,
    ):
        """Initialize the YouTube client and optional proxy-backed transcript API.

        Args:
            proxy_username: Optional proxy username for YouTube client.
            proxy_password: Optional proxy password for YouTube client.
            language: Preferred transcript language code.
        """
        self.languages = transcript_languages(language)
        self.ytt_api = YouTubeTranscriptApi()
        self.proxy_config = None
        if proxy_username and proxy_password:
            self.proxy_config = WebshareProxyConfig(
                proxy_username=proxy_username, proxy_password=proxy_password
            )
            logger.debug("Using Webshare proxy for transcript retrieval")
            self.ytt_api = YouTubeTranscriptApi(proxy_config=self.proxy_config)

    def get_video_transcript(  # pylint: disable=too-many-return-statements,too-many-branches
        self, url: str
    ) -> str:
        """Retrieve the transcript text for a YouTube video URL.

        The transcript API may return either a ``FetchedTranscript`` object or a
        list of snippet dictionaries. Both shapes are normalized into a single
        space-separated string. Unavailable transcripts return an empty string;
        unexpected API errors and malformed responses are logged and raised.

        Args:
            url: Full YouTube watch URL containing the ``v`` query parameter.

        Returns:
            The complete transcript text, or ``""`` when the video has no
            available transcript.

        Raises:
            TypeError: If a fetched transcript contains malformed snippets.
            SystemExit: If the transcript API returns an unsupported structure.
        """

        query = urlparse(url).query
        video_id = parse_qs(query)["v"][0]

        logger.info("Fetching transcript for video ID: %s", video_id)
        logger.debug("Transcript proxy enabled: %s", self.proxy_config is not None)
        fetch_started = time.monotonic()
        try:
            transcript = self.ytt_api.fetch(video_id, languages=self.languages)
        except AgeRestricted:
            logger.warning(
                "Video is age-restricted and cannot fetch transcript: %s "
                "(after %.2f seconds)",
                video_id,
                time.monotonic() - fetch_started,
            )
            return ""
        except NoTranscriptFound:
            logger.warning(
                "No transcript found for video ID %s in preferred languages %s "
                "(after %.2f seconds)",
                video_id,
                self.languages,
                time.monotonic() - fetch_started,
            )
            return ""
        except TranscriptsDisabled:
            logger.warning(
                "Transcripts are disabled for video ID: %s (after %.2f seconds)",
                video_id,
                time.monotonic() - fetch_started,
            )
            return ""
        except (VideoUnavailable, VideoUnplayable):
            logger.warning(
                "Video is unavailable or unplayable: %s (after %.2f seconds)",
                video_id,
                time.monotonic() - fetch_started,
            )
            return ""
        except Exception:
            logger.exception(
                "Error fetching transcript for video ID %s after %.2f seconds",
                video_id,
                time.monotonic() - fetch_started,
            )
            raise

        logger.debug(
            "Transcript fetch completed for video ID %s in %.2f seconds "
            "(response type: %s)",
            video_id,
            time.monotonic() - fetch_started,
            type(transcript).__name__,
        )

        # Handle FetchedTranscript type
        if hasattr(transcript, "snippets"):
            try:
                processed_snippet_count = 0
                transcript_parts = []

                for snippet in transcript.snippets:
                    if not hasattr(snippet, "text"):
                        logger.error(
                            "Unexpected snippet type for video ID %s: %s",
                            video_id,
                            type(snippet),
                        )
                        raise TypeError("Unsupported snippet type encountered.")
                    transcript_parts.append(snippet.text)
                    processed_snippet_count += 1

                # Handle FetchedTranscriptSnippet objects properly
                if transcript_parts:
                    transcript_text = " ".join(transcript_parts)
                else:
                    logger.error("FetchedTranscript did not contain any snippets.")
                    raise TypeError("FetchedTranscript contains no snippets.")
                logger.debug(
                    "Successfully processed transcript for video ID %s: "
                    "%d snippets, %d characters",
                    video_id,
                    processed_snippet_count,
                    len(transcript_text),
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
                transcript_text = " ".join(snippet["text"] for snippet in transcript)
                logger.debug(
                    "Successfully processed transcript for video ID %s: "
                    "%d snippets, %d characters",
                    video_id,
                    len(transcript),
                    len(transcript_text),
                )
                return transcript_text
            logger.error(
                "Transcript list for video ID %s contains %d invalid snippet "
                "structure(s)",
                video_id,
                sum(
                    not isinstance(snippet, dict) or "text" not in snippet
                    for snippet in transcript
                ),
            )
        else:
            logger.error(
                "Unexpected transcript structure for video ID %s: %s",
                video_id,
                type(transcript).__name__,
            )
            raise SystemExit("Critical error: Unexpected transcript structure.")

        return ""

    def get_video_title(self, url: str) -> str:
        """Extract the video title from the YouTube page.

        Parses the video page HTML and extracts the title from the Open Graph
        meta tag (``og:title``), optionally routing the request through the
        configured proxy.

        Args:
            url: Full YouTube video URL.

        Returns:
            The video title, or ``"Title not found"`` when the page request or
            metadata extraction fails.
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
            title_content = title_tag.get("content") if title_tag else None
            title = str(title_content).strip() if title_content else "Title not found"
            logger.debug("Successfully retrieved title: %s", title)
            return title
        except (
            requests.exceptions.RequestException,
            requests.exceptions.HTTPError,
        ) as e:
            logger.error("Failed to fetch title for video URL %s: %s", url, e)
            return "Title not found"
