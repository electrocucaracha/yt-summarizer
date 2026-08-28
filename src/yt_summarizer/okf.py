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

"""Filesystem storage backend using the Open Knowledge Format (OKF).

Persists playlists and videos as a bundle of markdown files with YAML
frontmatter, as described by the OKF specification (https://okf.md/spec/).

The generated layout is::

    docs/
    ├── index.md                    # Bundle index listing every playlist
    ├── <playlist>.md               # Playlist concept (executive summary)
    └── <playlist>/
        ├── index.md                # Playlist index listing every video
        ├── README.md               # Executive summary plus every video summary
        └── <video-id>.md           # One concept per video

This backend is an alternative to Notion, so the application can run without
any Notion credentials.
"""

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .model import YouTubeVideo

logger = logging.getLogger(__name__)

DEFAULT_ROOT = "docs"
DEFAULT_PLAYLIST_TITLE = "Videos"
OKF_VERSION = "0.1"
PLAYLIST_TYPE = "YouTube Playlist"
VIDEO_TYPE = "YouTube Video"
_RESERVED_FILENAMES = frozenset({"index.md", "log.md", "README.md"})


def slugify(value: str) -> str:
    """Convert an arbitrary title into a filesystem-friendly slug.

    Examples:
        >>> slugify("Kubernetes 101: The Basics!")
        'kubernetes-101-the-basics'
        >>> slugify("   ")
        'untitled'
    """
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "untitled"


def extract_video_id(url: str) -> str:
    """Return the stable YouTube video identifier contained in ``url``.

    Examples:
        >>> extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
        >>> extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
    """
    parsed = urlparse(url)
    video_id = parse_qs(parsed.query).get("v", [""])[0]
    if not video_id:
        video_id = parsed.path.rsplit("/", 1)[-1]
    return video_id or slugify(url)


def _escape_yaml(value: str) -> str:
    """Quote a scalar so it survives a YAML frontmatter round-trip.

    Examples:
        >>> _escape_yaml('He said "hi": ok')
        '"He said \\\\"hi\\\\": ok"'
    """
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _render_frontmatter(fields: dict[str, str]) -> str:
    """Render an ordered mapping as a YAML frontmatter block."""
    lines = ["---"]
    for key, value in fields.items():
        lines.append(f"{key}: {_escape_yaml(value)}")
    lines.append("---")
    return "\n".join(lines)


def _parse_frontmatter(content: str) -> dict[str, str]:
    """Parse the frontmatter emitted by :func:`_render_frontmatter`.

    Examples:
        >>> _parse_frontmatter('---\\ntype: "A"\\ntitle: "B"\\n---\\nbody')
        {'type': 'A', 'title': 'B'}
        >>> _parse_frontmatter('no frontmatter')
        {}
    """
    if not content.startswith("---\n"):
        return {}
    _, _, remainder = content.partition("---\n")
    block, separator, _ = remainder.partition("\n---")
    if not separator:
        return {}

    fields = {}
    for line in block.splitlines():
        key, delimiter, value = line.partition(":")
        if not delimiter:
            continue
        value = value.strip()
        if value.startswith('"') and value.endswith('"') and len(value) > 1:
            value = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        fields[key.strip()] = value
    return fields


def _extract_section(content: str, heading: str) -> str:
    """Return the body of a top-level markdown section, or an empty string.

    Examples:
        >>> _extract_section("# Summary\\n\\ntext\\n\\n# Main Points\\n\\n- a", "Summary")
        'text'
        >>> _extract_section("# Summary\\n\\ntext", "Missing")
        ''
    """
    match = re.search(
        rf"^# {re.escape(heading)}\s*$(.*?)(?=^# |\Z)",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


class Client:
    """Read and write a YouTube knowledge bundle on the local filesystem."""

    def __init__(self, root: str = DEFAULT_ROOT):
        """Initialize the store.

        Args:
            root: Root folder of the OKF bundle (default: ``docs``).
        """
        self.root = Path(root)
        logger.debug("Initializing OKF client with root: %s", self.root)

    def playlist_dir(self, playlist_title: str | None) -> Path:
        """Return the directory holding the concepts of a playlist."""
        return self.root / slugify(playlist_title or DEFAULT_PLAYLIST_TITLE)

    def _video_path(self, playlist_title: str | None, video: YouTubeVideo) -> Path:
        return self.playlist_dir(playlist_title) / f"{extract_video_id(video.url)}.md"

    def get_videos(self, playlist_title: str | None = None) -> list[YouTubeVideo]:
        """Load every video concept already stored for a playlist.

        Args:
            playlist_title: Playlist whose concepts should be loaded.

        Returns:
            A list of ``YouTubeVideo`` objects rebuilt from the markdown files.
            Files without a ``resource`` URL are ignored.
        """
        directory = self.playlist_dir(playlist_title)
        if not directory.is_dir():
            logger.info("No existing OKF bundle found at %s", directory)
            return []

        videos = []
        for path in sorted(directory.glob("*.md")):
            if path.name in _RESERVED_FILENAMES:
                continue
            content = path.read_text(encoding="utf-8")
            fields = _parse_frontmatter(content)
            url = fields.get("resource", "")
            if not url:
                logger.warning("Skipping %s: no 'resource' URL in frontmatter", path)
                continue
            videos.append(
                YouTubeVideo(
                    url=url,
                    title=fields.get("title", ""),
                    summary=_extract_section(content, "Summary"),
                    main_points=_extract_section(content, "Main Points"),
                )
            )

        logger.info("Loaded %d video(s) from OKF bundle at %s", len(videos), directory)
        return videos

    def write_video(
        self, video: YouTubeVideo, playlist_title: str | None = None
    ) -> Path:
        """Write a single video concept document.

        Args:
            video: The video to persist.
            playlist_title: Playlist the video belongs to.

        Returns:
            The path of the written markdown file.
        """
        path = self._video_path(playlist_title, video)
        path.parent.mkdir(parents=True, exist_ok=True)

        frontmatter = _render_frontmatter(
            {
                "type": VIDEO_TYPE,
                "title": video.title or video.url,
                "description": _first_sentence(video.summary),
                "resource": video.url,
                "timestamp": _now(),
            }
        )
        body = (
            f"# Summary\n\n{video.summary or '_Not available yet._'}\n\n"
            f"# Main Points\n\n{video.main_points or '_Not available yet._'}\n\n"
            f"# Citations\n\n[1] [{video.title or 'YouTube video'}]({video.url})\n"
        )
        path.write_text(f"{frontmatter}\n\n{body}", encoding="utf-8")
        logger.debug("Wrote video concept: %s", path)
        return path

    def write_playlist(
        self,
        videos: list[YouTubeVideo],
        playlist_title: str | None = None,
        playlist_summary: str = "",
        playlist_url: str | None = None,
    ) -> Path:
        """Write the playlist concept, its index, and the bundle root index.

        Args:
            videos: Videos belonging to the playlist.
            playlist_title: Human-readable playlist name.
            playlist_summary: Executive summary of the whole playlist.
            playlist_url: Canonical playlist URL, when known.

        Returns:
            The path of the playlist concept document.
        """
        title = playlist_title or DEFAULT_PLAYLIST_TITLE
        slug = slugify(title)
        directory = self.playlist_dir(title)
        directory.mkdir(parents=True, exist_ok=True)

        fields = {
            "type": PLAYLIST_TYPE,
            "title": title,
            "description": _first_sentence(playlist_summary),
            "timestamp": _now(),
        }
        if playlist_url:
            fields["resource"] = playlist_url

        entries = "\n".join(
            f"* [{video.title or video.url}](/{slug}/{extract_video_id(video.url)}.md)"
            f" - {_first_sentence(video.summary)}".rstrip(" -")
            for video in videos
        )
        playlist_path = self.root / f"{slug}.md"
        playlist_path.write_text(
            f"{_render_frontmatter(fields)}\n\n"
            f"# Executive Summary\n\n{playlist_summary or '_Not available yet._'}\n\n"
            f"# Videos\n\n{entries}\n",
            encoding="utf-8",
        )

        (directory / "index.md").write_text(
            f"# {title}\n\n{entries}\n", encoding="utf-8"
        )
        self._write_playlist_readme(directory, title, playlist_summary, videos)
        self._write_root_index()
        logger.info("Wrote OKF playlist bundle: %s", playlist_path)
        return playlist_path

    def _write_playlist_readme(
        self,
        directory: Path,
        title: str,
        playlist_summary: str,
        videos: list[YouTubeVideo],
    ) -> None:
        """Write the playlist README aggregating the summary of every concept."""
        sections = []
        for video in videos:
            heading = video.title or video.url
            sections.append(
                f"### [{heading}]({extract_video_id(video.url)}.md)\n\n"
                f"Source: <{video.url}>\n\n"
                f"{video.summary or '_Not available yet._'}"
            )

        (directory / "README.md").write_text(
            f"# {title}\n\n"
            f"## Executive Summary\n\n{playlist_summary or '_Not available yet._'}\n\n"
            f"## Video Summaries\n\n" + "\n\n".join(sections) + "\n",
            encoding="utf-8",
        )

    def _write_root_index(self) -> None:
        """Regenerate the bundle root index from the playlist concepts."""
        entries = []
        for path in sorted(self.root.glob("*.md")):
            if path.name in _RESERVED_FILENAMES:
                continue
            fields = _parse_frontmatter(path.read_text(encoding="utf-8"))
            title = fields.get("title", path.stem)
            description = fields.get("description", "")
            entries.append(f"* [{title}]({path.name}) - {description}".rstrip(" -"))

        (self.root / "index.md").write_text(
            f'---\nokf_version: "{OKF_VERSION}"\n---\n\n'
            "# Playlists\n\n" + "\n".join(entries) + "\n",
            encoding="utf-8",
        )


def _now() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _first_sentence(text: str, limit: int = 200) -> str:
    """Return a one-line description derived from ``text``.

    Examples:
        >>> _first_sentence("First one. Second one.")
        'First one.'
        >>> _first_sentence("")
        ''
    """
    flattened = " ".join(text.split())
    if not flattened:
        return ""
    head, separator, _ = flattened.partition(". ")
    sentence = (head + separator).strip()
    if len(sentence) > limit:
        sentence = sentence[: limit - 3] + "..."
    return sentence
