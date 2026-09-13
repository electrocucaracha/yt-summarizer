"""Tests for the OKF filesystem storage backend."""

import re
import tempfile
import unittest
from pathlib import Path
from shutil import rmtree

import yaml

from yt_summarizer.model import YouTubeVideo
from yt_summarizer.okf import Client, extract_video_id


class TestOKFClient(unittest.TestCase):
    """Tests for the OKF bundle client."""

    def setUp(self):
        """Create an isolated bundle root for each test."""
        self.root = Path(tempfile.mkdtemp()) / "docs"
        self.addCleanup(rmtree, self.root.parent)
        self.client = Client(root=str(self.root))
        self.video = YouTubeVideo(
            url="https://www.youtube.com/watch?v=Video1ABC",
            title="Intro to Kubernetes",
            summary="A short intro. More detail follows.",
            main_points="- pods\n- services",
        )

    def test_extract_video_id_lowercases(self):
        """Video ID extraction should normalize IDs to lowercase filenames."""
        self.assertEqual(
            "video1abc", extract_video_id("https://www.youtube.com/watch?v=Video1ABC")
        )
        self.assertEqual(
            "dqw4w9wgxcq", extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        )

    def test_write_video_creates_concept_under_playlist_folder(self):
        """Each video should become a markdown concept inside the playlist folder with lowercase ID."""
        path = self.client.write_video(self.video, playlist_title="K8s Weekly")

        self.assertEqual(self.root / "k8s-weekly" / "video1abc.md", path)
        content = path.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---\n"))
        self.assertIn("type: Video Note", content)
        self.assertIn("layout: default", content)
        self.assertIn("parent: K8s Weekly", content)
        self.assertIn(self.video.url, content)
        self.assertIn("- k8s-weekly", content)
        self.assertIn("- video", content)
        self.assertIn("- learning", content)
        self.assertIn("status: stable", content)
        self.assertIn("by: process:yt-summarizer-okf", content)
        self.assertIn("# Summary", content)
        self.assertIn("# Main Points", content)
        self.assertIn("|   # | Main point |", content)
        self.assertIn("# Video", content)
        self.assertIn(f"[Watch on YouTube]({self.video.url})", content)

    def test_get_videos_round_trips_written_concepts(self):
        """Videos written to the bundle should be readable back."""
        self.client.write_video(self.video, playlist_title="K8s Weekly")

        videos = self.client.get_videos("K8s Weekly")

        self.assertEqual(1, len(videos))
        self.assertEqual(self.video.url, videos[0].url)
        self.assertEqual(self.video.title, videos[0].title)
        self.assertIn("A short intro.", videos[0].summary)
        self.assertIn("|   # | Main point |", videos[0].main_points)

    def test_has_video_and_get_video(self):
        """has_video and get_video should detect and retrieve stored concepts."""
        self.assertFalse(self.client.has_video(self.video, "K8s Weekly"))
        self.assertIsNone(self.client.get_video(self.video, "K8s Weekly"))

        self.client.write_video(self.video, playlist_title="K8s Weekly")

        self.assertTrue(self.client.has_video(self.video, "K8s Weekly"))
        retrieved = self.client.get_video(self.video, "K8s Weekly")
        self.assertIsNotNone(retrieved)
        self.assertEqual(self.video.url, retrieved.url)
        self.assertEqual(self.video.title, retrieved.title)

    def test_get_videos_returns_empty_list_for_unknown_playlist(self):
        """Missing playlist folders should not raise."""
        self.assertEqual([], self.client.get_videos("Never Written"))

    def test_write_playlist_creates_indexes_and_executive_report(self):
        """The playlist concept, executive report, and both index files should be generated."""
        self.client.write_video(self.video, playlist_title="K8s Weekly")

        playlist_path = self.client.write_playlist(
            [self.video],
            playlist_title="K8s Weekly",
            playlist_summary="Everything about Kubernetes. It covers containers and orchestration.",
            playlist_url="https://youtube.com/playlist?list=abc123",
        )

        self.assertEqual(self.root / "k8s-weekly" / "index.md", playlist_path)

        playlist_index = (self.root / "k8s-weekly" / "index.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("layout: default", playlist_index)
        self.assertIn("title: K8s Weekly", playlist_index)
        self.assertIn("has_children: true", playlist_index)
        self.assertIn('okf_version: "0.2"', playlist_index)
        self.assertIn("# K8s Weekly", playlist_index)
        self.assertIn("## Concepts", playlist_index)
        self.assertIn("- [Intro to Kubernetes](video1abc.md)", playlist_index)

        # Executive report README.md
        readme_path = self.root / "k8s-weekly" / "README.md"
        self.assertTrue(readme_path.is_file())
        readme_content = readme_path.read_text(encoding="utf-8")
        self.assertIn("type: Executive Report", readme_content)
        self.assertIn("Executive Report: K8s Weekly", readme_content)
        self.assertIn("parent: K8s Weekly", readme_content)
        self.assertIn("nav_order: 1", readme_content)
        self.assertIn("# Executive Report: K8s Weekly", readme_content)
        self.assertIn("## Executive Overview", readme_content)
        self.assertIn("Everything about Kubernetes.", readme_content)

        # Root index
        root_index = (self.root / "index.md").read_text(encoding="utf-8")
        self.assertIn('okf_version: "0.2"', root_index)
        self.assertIn("layout: default", root_index)
        self.assertIn("title: Home", root_index)
        self.assertIn("nav_order: 1", root_index)
        self.assertIn("# Conference Knowledge Collections", root_index)
        self.assertIn("## Collections", root_index)
        self.assertIn("- [K8s Weekly (1 note)](k8s-weekly/index.md)", root_index)

    def test_write_playlist_creates_config_and_log(self):
        """The bundle root should include _config.yml and log.md."""
        self.client.write_playlist(
            [self.video],
            playlist_title="K8s Weekly",
            playlist_summary="Everything about Kubernetes.",
        )

        config_content = (self.root / "_config.yml").read_text(encoding="utf-8")
        self.assertIn("remote_theme: just-the-docs/just-the-docs", config_content)
        self.assertIn("enable_copy_code_button: true", config_content)

        log_content = (self.root / "log.md").read_text(encoding="utf-8")
        self.assertIn("layout: default", log_content)
        self.assertIn("title: Directory Update Log", log_content)
        self.assertIn("nav_exclude: true", log_content)
        self.assertIn("# Directory Update Log", log_content)

    def test_bundle_conforms_to_okf_checker(self):
        """The generated bundle should pass OKF v0.2 structural validation."""
        self.client.write_video(self.video, playlist_title="K8s Weekly")
        self.client.write_playlist(
            [self.video],
            playlist_title="K8s Weekly",
            playlist_summary="Full summary of the playlist.",
        )

        # Validate bundle structure matching yt-conferences check_okf.py
        index_path = self.root / "index.md"
        self.assertTrue(index_path.is_file())
        self.assertIn('okf_version: "0.2"', index_path.read_text(encoding="utf-8"))

        directories = [
            p for p in self.root.rglob("*") if p.is_dir() and "assets" not in p.parts
        ]
        for directory in directories:
            self.assertTrue(
                (directory / "index.md").is_file(), f"Missing index.md in {directory}"
            )

        for path in self.root.rglob("*.md"):
            if path.name in {"index.md", "log.md", "README.md"}:
                continue
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"))
            _, _, remainder = text.partition("---\n")
            frontmatter_block, _, body = remainder.partition("\n---")
            meta = yaml.safe_load(frontmatter_block)
            self.assertTrue(bool(meta.get("type")))
            for section in ["# Summary", "# Main Points", "# Video"]:
                self.assertIn(section, body)
            self.assertTrue(
                re.search(r"^\|\s*#\s*\|\s*Main point\s*\|", body, re.MULTILINE)
            )
            self.assertTrue(
                re.search(r"^\|\s*:?-+:\s*\|\s*-+\s*\|", body, re.MULTILINE)
            )

    def test_get_videos_ignores_reserved_files(self):
        """Reserved bundle files should never be read back as video concepts."""
        self.client.write_video(self.video, playlist_title="K8s Weekly")
        self.client.write_playlist([self.video], playlist_title="K8s Weekly")

        self.assertEqual(1, len(self.client.get_videos("K8s Weekly")))


if __name__ == "__main__":
    unittest.main()
