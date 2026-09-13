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
    ├── _config.yml                 # Theme configuration
    ├── log.md                      # Directory update log
    ├── index.md                    # Bundle index listing every playlist
    └── <playlist>/
        ├── index.md                # Playlist index listing every video
        └── <video-id>.md           # One concept per video

This backend is an alternative to Notion, so the application can run without
any Notion credentials.
"""

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .model import YouTubeVideo

logger = logging.getLogger(__name__)

DEFAULT_ROOT = "docs"
DEFAULT_PLAYLIST_TITLE = "Videos"
OKF_VERSION = "0.2"
PLAYLIST_TYPE = "YouTube Playlist"
VIDEO_TYPE = "Video Note"
_RESERVED_FILENAMES = frozenset({"index.md", "log.md", "_config.yml", "README.md"})


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


def _render_frontmatter(fields: dict[str, Any]) -> str:
    """Render an ordered mapping as a YAML frontmatter block."""
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, list):
            items = ", ".join(_escape_yaml(x) if isinstance(x, str) else str(x) for x in value)
            lines.append(f"{key}: [{items}]")
        elif isinstance(value, dict):
            items = ", ".join(
                f"{k}: {_escape_yaml(v) if isinstance(v, str) and ' ' in v else v}"
                for k, v in value.items()
            )
            lines.append(f"{key}: {{ {items} }}")
        elif isinstance(value, str):
            if key == "type":
                lines.append(f"{key}: {value}")
            else:
                lines.append(f"{key}: {_escape_yaml(value)}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def _format_summary(text: str) -> str:
    """Format summary text into semantic sentences, one per line."""
    if not text or not text.strip():
        return "_Not available yet._"
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
        if sentence.strip()
    ]
    return "\n".join(sentences) if sentences else "_Not available yet._"


def _format_main_points_table(text: str) -> str:
    """Format main points as a Markdown table complying with OKF v0.2."""
    if not text or not text.strip():
        return "|   # | Main point |\n| --: | ---------- |\n|   1 | _Not available yet._ |"

    stripped = text.strip()
    if "|   # | Main point |" in stripped or ("|" in stripped and "\n|" in stripped):
        return stripped

    points = []
    for line in stripped.splitlines():
        line = line.strip()
        if not line:
            continue
        cleaned = re.sub(r"^([*+\-\d\w]+[.)\]]?\s*)+", "", line).strip()
        if cleaned:
            points.append(cleaned)

    if not points:
        return "|   # | Main point |\n| --: | ---------- |\n|   1 | _Not available yet._ |"

    table_lines = ["|   # | Main point |", "| --: | ---------- |"]
    for idx, point in enumerate(points, 1):
        clean_point = point.replace("|", "\\|").strip()
        table_lines.append(f"| {idx:3d} | {clean_point} |")

    return "\n".join(table_lines)


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

        playlist_slug = slugify(playlist_title or DEFAULT_PLAYLIST_TITLE)
        frontmatter = _render_frontmatter(
            {
                "type": VIDEO_TYPE,
                "title": video.title or video.url,
                "description": _first_sentence(video.summary),
                "resource": video.url,
                "tags": [playlist_slug, "video", "learning"],
                "status": "stable",
                "generated": {
                    "by": "process:yt-summarizer-okf",
                    "at": _now(),
                },
            }
        )
        body = (
            f"# Summary\n\n{_format_summary(video.summary)}\n\n"
            f"# Main Points\n\n{_format_main_points_table(video.main_points)}\n\n"
            f"# Video\n\n[Watch on YouTube]({video.url})\n"
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
        """Write the playlist index and the bundle root index conforming to OKF v0.2.

        Args:
            videos: Videos belonging to the playlist.
            playlist_title: Human-readable playlist name.
            playlist_summary: Executive summary of the whole playlist.
            playlist_url: Canonical playlist URL, when known.

        Returns:
            The path of the playlist index document.
        """
        title = playlist_title or DEFAULT_PLAYLIST_TITLE
        slug = slugify(title)
        directory = self.playlist_dir(title)
        directory.mkdir(parents=True, exist_ok=True)

        self._write_config_yml()
        self._write_log_md()

        # Clean up legacy files if present
        legacy_file = self.root / f"{slug}.md"
        if legacy_file.is_file():
            legacy_file.unlink()
        legacy_readme = directory / "README.md"
        if legacy_readme.is_file():
            legacy_readme.unlink()

        entries = "\n".join(
            f"- [{video.title or video.url}]({extract_video_id(video.url)}.md)"
            f" - {_first_sentence(video.summary)}".rstrip(" -")
            for video in videos
        )

        playlist_index_path = directory / "index.md"
        playlist_index_path.write_text(
            f"# {title}\n\n## Concepts\n\n{entries}\n",
            encoding="utf-8",
        )

        self._write_root_index()
        logger.info("Wrote OKF playlist bundle: %s", playlist_index_path)
        return playlist_index_path

    def _write_config_yml(self) -> None:
        """Write docs/_config.yml for theme support."""
        config_path = self.root / "_config.yml"
        if not config_path.is_file():
            config_path.write_text(
                "remote_theme: just-the-docs/just-the-docs\n"
                "enable_copy_code_button: true\n",
                encoding="utf-8",
            )

    def _write_log_md(self) -> None:
        """Write or maintain docs/log.md for bundle updates."""
        log_path = self.root / "log.md"
        if not log_path.is_file():
            today = datetime.now(UTC).strftime("%Y-%m-%d")
            log_path.write_text(
                "# Directory Update Log\n\n"
                f"## {today}\n\n"
                "- **Creation**: Built the OKF v0.2 knowledge bundle from YouTube videos.\n",
                encoding="utf-8",
            )

    def _write_root_index(self) -> None:
        """Regenerate the bundle root index from the playlist directories."""
        entries = []
        if self.root.is_dir():
            for path in sorted(self.root.iterdir()):
                if not path.is_dir() or path.name.startswith("."):
                    continue
                index_path = path / "index.md"
                if not index_path.is_file():
                    continue

                concept_count = sum(
                    1 for f in path.glob("*.md") if f.name not in _RESERVED_FILENAMES
                )
                note_label = "1 note" if concept_count == 1 else f"{concept_count} notes"

                title = path.name.replace("-", " ").title()
                content = index_path.read_text(encoding="utf-8")
                match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                if match:
                    title = match.group(1).strip()

                entries.append(
                    f"- [{title} ({note_label})]({path.name}/index.md) - Topic collection"
                )

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
