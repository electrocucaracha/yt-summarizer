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

"""Data model for YouTube video information.

Defines the YouTubeVideo class which represents a YouTube video with all its
metadata including transcript, summaries, and extracted key points. This class
serves as the core data structure for the application.
"""

import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class YouTubeVideo:
    """Represents a YouTube video with its metadata and analysis results.

    Attributes:
        id: Unique identifier for the video in the Notion database.
        url: The YouTube video URL.
        title: The video title extracted from YouTube.
        transcript: The complete video transcript.
        summary: LLM-generated summary of the video content.
        main_points: LLM-extracted key points and takeaways from the video.

    Example:
        >>> video = YouTubeVideo(
        ...     url="https://www.youtube.com/watch?v=demo",
        ...     title="Demo",
        ...     summary="Concise summary.",
        ... )
        >>> str(video).splitlines() == [
        ...     "URL: https://www.youtube.com/watch?v=demo",
        ...     "Title: Demo",
        ...     "Transcript: ",
        ...     "Summary: Concise summary.",
        ...     "Main Points: ",
        ... ]
        True
    """

    # pylint: disable=redefined-builtin,too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        url: str,
        id: Optional[str] = None,
        title: str = "",
        transcript: str = "",
        summary: str = "",
        main_points: str = "",
    ):
        """Initialize a YouTubeVideo instance.

        Args:
            id: Unique identifier for the video in the database.
            url: Full YouTube video URL.
            title: Video title (optional, can be filled later).
            transcript: Video transcript text (optional, can be filled later).
            summary: Generated summary (optional, can be filled later).
            main_points: Extracted key points (optional, can be filled later).
        """
        self.id = id
        self.url = url
        self.title = title
        self.transcript = transcript
        self.summary = summary
        self.main_points = main_points

    def __repr__(self):
        """Return a detailed representation of the YouTubeVideo object.

        Shows content lengths for debugging and logging purposes.
        """
        return (
            f"YouTubeVideo(url={self.url}, title={self.title}, "
            f"transcript_length={len(self.transcript) if self.transcript else 0}, "
            f"summary_length={len(self.summary) if self.summary else 0}, "
            f"main_points_length={len(self.main_points) if self.main_points else 0})"
        )

    def __str__(self):
        """Return a human-readable string representation of the video data.

        Displays all video information in a formatted multi-line output.
        """
        return (
            f"URL: {self.url}\nTitle: {self.title}\n"
            f"Transcript: {self.transcript}\nSummary: {self.summary}\n"
            f"Main Points: {self.main_points}"
        )

    def compute_hash(self):
        """Compute a content hash for change detection.

        The hash currently ignores ``id`` and ``transcript`` because Notion
        writes are triggered only by changes to the persisted presentation
        fields.

        Examples:
            >>> first = YouTubeVideo(
            ...     url="https://www.youtube.com/watch?v=demo",
            ...     title="Demo",
            ...     transcript="first transcript",
            ...     summary="Summary",
            ...     main_points="- point",
            ... )
            >>> second = YouTubeVideo(
            ...     url="https://www.youtube.com/watch?v=demo",
            ...     title="Demo",
            ...     transcript="updated transcript",
            ...     summary="Summary",
            ...     main_points="- point",
            ... )
            >>> first.compute_hash() == second.compute_hash()
            True
        """
        data = f"{self.title}{self.url}{self.summary}{self.main_points}"
        return hashlib.sha256(data.encode()).hexdigest()
