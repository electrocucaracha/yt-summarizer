"""Tests for the OKF filesystem storage backend."""

import tempfile
import unittest
from pathlib import Path
from shutil import rmtree

from yt_summarizer.model import YouTubeVideo
from yt_summarizer.okf import Client


class TestOKFClient(unittest.TestCase):
    """Tests for the OKF bundle client."""

    def setUp(self):
        """Create an isolated bundle root for each test."""
        self.root = Path(tempfile.mkdtemp()) / "docs"
        self.addCleanup(rmtree, self.root.parent)
        self.client = Client(root=str(self.root))
        self.video = YouTubeVideo(
            url="https://www.youtube.com/watch?v=video1",
            title="Intro to Kubernetes",
            summary="A short intro. More detail follows.",
            main_points="- pods\n- services",
        )

    def test_write_video_creates_concept_under_playlist_folder(self):
        """Each video should become a markdown concept inside the playlist folder."""
        path = self.client.write_video(self.video, playlist_title="K8s Weekly")

        self.assertEqual(self.root / "k8s-weekly" / "video1.md", path)
        content = path.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---\n"))
        self.assertIn("type: Video Note", content)
        self.assertIn(f'resource: "{self.video.url}"', content)
        self.assertIn("# Summary", content)
        self.assertIn("# Main Points", content)
        self.assertIn("|   # | Main point |", content)
        self.assertIn("# Video", content)

    def test_get_videos_round_trips_written_concepts(self):
        """Videos written to the bundle should be readable back."""
        self.client.write_video(self.video, playlist_title="K8s Weekly")

        videos = self.client.get_videos("K8s Weekly")

        self.assertEqual(1, len(videos))
        self.assertEqual(self.video.url, videos[0].url)
        self.assertEqual(self.video.title, videos[0].title)
        self.assertIn("A short intro.", videos[0].summary)
        self.assertIn("|   # | Main point |", videos[0].main_points)

    def test_get_videos_returns_empty_list_for_unknown_playlist(self):
        """Missing playlist folders should not raise."""
        self.assertEqual([], self.client.get_videos("Never Written"))

    def test_write_playlist_creates_indexes_and_playlist_concept(self):
        """The playlist concept and both index files should be generated."""
        self.client.write_video(self.video, playlist_title="K8s Weekly")

        playlist_path = self.client.write_playlist(
            [self.video],
            playlist_title="K8s Weekly",
            playlist_summary="Everything about Kubernetes.",
            playlist_url="https://youtube.com/playlist?list=abc123",
        )

        self.assertEqual(self.root / "k8s-weekly" / "index.md", playlist_path)

        playlist_index = (self.root / "k8s-weekly" / "index.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("# K8s Weekly", playlist_index)
        self.assertIn("## Concepts", playlist_index)
        self.assertIn("- [Intro to Kubernetes](video1.md)", playlist_index)

        root_index = (self.root / "index.md").read_text(encoding="utf-8")
        self.assertIn('okf_version: "0.2"', root_index)
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

        log_content = (self.root / "log.md").read_text(encoding="utf-8")
        self.assertIn("# Directory Update Log", log_content)

    def test_get_videos_ignores_reserved_files(self):
        """Reserved bundle files should never be read back as video concepts."""
        self.client.write_video(self.video, playlist_title="K8s Weekly")
        self.client.write_playlist([self.video], playlist_title="K8s Weekly")

        self.assertEqual(1, len(self.client.get_videos("K8s Weekly")))


if __name__ == "__main__":
    unittest.main()
