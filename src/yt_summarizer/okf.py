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

import yaml

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
        'dqw4w9wgxcq'
        >>> extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        'dqw4w9wgxcq'
    """
    parsed = urlparse(url)
    video_id = parse_qs(parsed.query).get("v", [""])[0]
    if not video_id:
        video_id = parsed.path.rsplit("/", 1)[-1]
    video_id = video_id.strip()
    return video_id.lower() if video_id else slugify(url)


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
        if value is not None:
            lines.extend(_render_frontmatter_field(key, value))
    lines.append("---")
    return "\n".join(lines)


def _render_frontmatter_field(key: str, value: Any) -> list[str]:
    """Render one frontmatter field."""
    if isinstance(value, list):
        return [f"{key}:", *(f"  - {item}" for item in value)]
    if isinstance(value, dict):
        return _render_frontmatter_mapping(key, value)
    return [f"{key}: {_render_frontmatter_scalar(key, value)}"]


def _render_frontmatter_mapping(key: str, value: dict[str, Any]) -> list[str]:
    """Render a nested mapping field."""
    lines = [f"{key}:"]
    for nested_key, nested_value in value.items():
        rendered_value = _render_mapping_scalar(nested_value)
        lines.append(f"  {nested_key}: {rendered_value}")
    return lines


def _render_mapping_scalar(value: Any) -> str:
    """Render a scalar nested in a frontmatter mapping."""
    if isinstance(value, str) and (
        ": " in value
        or value.startswith(("@", "%", "[", "{", "*", "&", "?", "|", ">", '"', "'", "#"))
        or "\n" in value
    ):
        return _escape_yaml(value)
    return str(value)


def _render_frontmatter_scalar(key: str, value: Any) -> str:
    """Render a scalar value, quoting strings when YAML requires it."""
    if isinstance(value, str):
        if key in {"type", "layout", "status"}:
            return value
        if key == "okf_version":
            return f'"{value}"'
        return _escape_yaml(value) if _requires_yaml_quoting(value) else value
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _requires_yaml_quoting(value: str) -> bool:
    """Return whether a plain YAML scalar needs quoting."""
    special_characters = ':"\\{}[],&*#?|->=!%@`\n'
    return (
        any(character in value for character in special_characters)
        or value.startswith(" ")
        or value.endswith(" ")
    )


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
        return (
            "|   # | Main point |\n| --: | ---------- |\n|   1 | _Not available yet._ |"
        )

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
        return (
            "|   # | Main point |\n| --: | ---------- |\n|   1 | _Not available yet._ |"
        )

    table_lines = ["|   # | Main point |", "| --: | ---------- |"]
    for idx, point in enumerate(points, 1):
        clean_point = point.replace("|", "\\|").strip()
        table_lines.append(f"| {idx:3d} | {clean_point} |")

    return "\n".join(table_lines)


def _parse_frontmatter(content: str) -> dict[str, Any]:
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

    try:
        data = yaml.safe_load(block)
        if isinstance(data, dict):
            return data
    except (yaml.YAMLError, AttributeError, ValueError) as err:
        logger.debug("Failed to parse YAML frontmatter with PyYAML: %s", err)

    fields: dict[str, Any] = {}
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

    def has_video(self, video: YouTubeVideo, playlist_title: str | None = None) -> bool:
        """Check if a video note already exists on the filesystem and has a summary."""
        path = self._video_path(playlist_title, video)
        if not path.is_file():
            return False
        content = path.read_text(encoding="utf-8")
        summary = _extract_section(content, "Summary")
        return bool(summary and summary.strip() and summary != "_Not available yet._")

    def get_video(
        self, video: YouTubeVideo, playlist_title: str | None = None
    ) -> YouTubeVideo | None:
        """Read back an existing video concept from the filesystem, if present."""
        path = self._video_path(playlist_title, video)
        if not path.is_file():
            return None
        content = path.read_text(encoding="utf-8")
        fields = _parse_frontmatter(content)
        url = str(fields.get("resource", video.url))
        return YouTubeVideo(
            url=url,
            title=str(fields.get("title", video.title or "")),
            summary=_extract_section(content, "Summary"),
            main_points=_extract_section(content, "Main Points"),
        )

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
            url = str(fields.get("resource", ""))
            if not url:
                logger.warning("Skipping %s: no 'resource' URL in frontmatter", path)
                continue
            videos.append(
                YouTubeVideo(
                    url=url,
                    title=str(fields.get("title", "")),
                    summary=_extract_section(content, "Summary"),
                    main_points=_extract_section(content, "Main Points"),
                )
            )

        logger.info("Loaded %d video(s) from OKF bundle at %s", len(videos), directory)
        return videos

    def write_video(
        self,
        video: YouTubeVideo,
        playlist_title: str | None = None,
        nav_order: int | None = None,
    ) -> Path:
        """Write a single video concept document.

        Args:
            video: The video to persist.
            playlist_title: Playlist the video belongs to.
            nav_order: Optional navigation order within the playlist.

        Returns:
            The path of the written markdown file.
        """
        path = self._video_path(playlist_title, video)
        path.parent.mkdir(parents=True, exist_ok=True)

        title = playlist_title or DEFAULT_PLAYLIST_TITLE
        playlist_slug = slugify(title)

        frontmatter_fields: dict[str, Any] = {
            "layout": "default",
            "title": video.title or video.url,
        }
        if nav_order is not None:
            frontmatter_fields["nav_order"] = nav_order
        frontmatter_fields.update(
            {
                "parent": title,
                "type": VIDEO_TYPE,
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
        frontmatter = _render_frontmatter(frontmatter_fields)
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
        """Write the playlist index, executive report, and bundle root index.

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

        # Clean up legacy root-level markdown file if present
        legacy_file = self.root / f"{slug}.md"
        if legacy_file.is_file():
            legacy_file.unlink()

        # Write or update README.md (Executive Report) if playlist_summary is available
        if playlist_summary and playlist_summary.strip():
            self._write_executive_report(directory, title, slug, playlist_summary)
        else:
            legacy_readme = directory / "README.md"
            if legacy_readme.is_file():
                legacy_readme.unlink()

        # Write/update individual video concepts with nav_order
        for idx, video in enumerate(videos, 1):
            if not self._video_path(title, video).is_file() or video.summary:
                self.write_video(video, playlist_title=title, nav_order=idx)

        playlist_frontmatter = self._playlist_frontmatter(title, slug, playlist_url)

        playlist_index_path = directory / "index.md"
        playlist_index_path.write_text(
            f"{playlist_frontmatter}\n\n"
            f"# {title}\n\n## Concepts\n\n"
            + "\n".join(_playlist_entries(videos))
            + "\n",
            encoding="utf-8",
        )

        self._write_root_index()
        logger.info("Wrote OKF playlist bundle: %s", playlist_index_path)
        return playlist_index_path

    def _playlist_frontmatter(
        self, title: str, slug: str, playlist_url: str | None
    ) -> str:
        """Render frontmatter for a playlist index."""
        fields: dict[str, Any] = {
            "layout": "default",
            "title": title,
            "has_children": True,
            "nav_order": self._get_playlist_nav_order(slug),
            "okf_version": OKF_VERSION,
        }
        if playlist_url:
            fields["resource"] = playlist_url
        return _render_frontmatter(fields)

    def _write_executive_report(
        self, directory: Path, title: str, slug: str, summary: str
    ) -> Path:
        """Write the executive report README.md inside the playlist folder."""
        readme_path = directory / "README.md"
        frontmatter = _render_frontmatter(
            {
                "layout": "default",
                "title": f"Executive Report: {title}",
                "parent": title,
                "nav_order": 1,
                "type": "Executive Report",
                "okf_version": OKF_VERSION,
                "description": f"Executive report and summary of the {title} conference.",
                "tags": [slug, "executive-report"],
                "status": "stable",
            }
        )
        formatted_summary = _format_summary(summary)
        body = (
            f"# Executive Report: {title}\n\n"
            f"## Executive Overview\n\n"
            f"{formatted_summary}\n"
        )
        readme_path.write_text(f"{frontmatter}\n\n{body}", encoding="utf-8")
        return readme_path

    def _get_playlist_nav_order(self, current_slug: str) -> int:
        """Return the 1-based navigation order for a playlist within the bundle."""
        if not self.root.is_dir():
            return 2
        playlist_slugs = sorted(
            p.name
            for p in self.root.iterdir()
            if p.is_dir() and not p.name.startswith(".") and "assets" not in p.parts
        )
        if current_slug not in playlist_slugs:
            playlist_slugs.append(current_slug)
            playlist_slugs.sort()
        try:
            return playlist_slugs.index(current_slug) + 2
        except ValueError:
            return 2

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
            frontmatter = _render_frontmatter(
                {
                    "layout": "default",
                    "title": "Directory Update Log",
                    "nav_exclude": True,
                }
            )
            log_path.write_text(
                f"{frontmatter}\n\n"
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
                if (
                    not path.is_dir()
                    or path.name.startswith(".")
                    or "assets" in path.parts
                ):
                    continue
                index_path = path / "index.md"
                if not index_path.is_file():
                    continue

                concept_count = sum(
                    1 for f in path.glob("*.md") if f.name not in _RESERVED_FILENAMES
                )
                note_label = (
                    "1 note" if concept_count == 1 else f"{concept_count} notes"
                )

                title = path.name.replace("-", " ").title()
                content = index_path.read_text(encoding="utf-8")
                match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                if match:
                    title = match.group(1).strip()

                entries.append(
                    f"- [{title} ({note_label})]({path.name}/index.md) - Topic collection"
                )

        root_frontmatter = _render_frontmatter(
            {
                "layout": "default",
                "title": "Home",
                "nav_order": 1,
                "okf_version": OKF_VERSION,
            }
        )

        (self.root / "index.md").write_text(
            f"{root_frontmatter}\n\n"
            "# Conference Knowledge Collections\n\n"
            "## Collections\n\n" + "\n".join(entries) + "\n",
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


def _playlist_entries(videos: list[YouTubeVideo]) -> list[str]:
    """Render the concept links for a playlist index."""
    entries = []
    for video in videos:
        entry = f"- [{video.title or video.url}]({extract_video_id(video.url)}.md)"
        summary = _first_sentence(video.summary)
        if summary:
            entry += f" - {summary}"
        entries.append(entry)
    return entries
