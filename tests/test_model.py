"""Tests for the YouTubeVideo model."""

import unittest

from yt_summarizer.model import YouTubeVideo


class TestYouTubeVideo(unittest.TestCase):
    """Tests for the YouTubeVideo data model class."""

    def test_video_initialization(self):
        """Test that YouTubeVideo initializes with all expected attributes."""
        video = YouTubeVideo(
            id="123",
            url="https://youtube.com/video123",
            title="Sample Video",
            transcript="Sample transcript",
            summary="Sample summary",
            main_points=["Point 1", "Point 2"],
        )
        self.assertEqual(video.id, "123")
        self.assertEqual(video.url, "https://youtube.com/video123")
        self.assertEqual(video.title, "Sample Video")
        self.assertEqual(video.transcript, "Sample transcript")
        self.assertEqual(video.summary, "Sample summary")
        self.assertEqual(video.main_points, ["Point 1", "Point 2"])

    def test_video_initialization_defaults(self):
        video = YouTubeVideo(url="https://youtube.com/video")

        self.assertIsNone(video.id)
        self.assertEqual("", video.title)
        self.assertEqual("", video.transcript)
        self.assertEqual("", video.summary)
        self.assertEqual("", video.main_points)

    def test_string_representation_includes_all_fields(self):
        video = YouTubeVideo(
            url="https://youtube.com/video",
            title="Title",
            transcript="Transcript",
            summary="Summary",
            main_points="Points",
        )

        self.assertEqual(
            "URL: https://youtube.com/video\n"
            "Title: Title\n"
            "Transcript: Transcript\n"
            "Summary: Summary\n"
            "Main Points: Points",
            str(video),
        )
        self.assertEqual(
            "YouTubeVideo(url=https://youtube.com/video, title=Title, "
            "transcript_length=10, summary_length=7, main_points_length=6)",
            repr(video),
        )

    def test_equality_and_hash_use_persisted_content(self):
        original = YouTubeVideo(
            id="one",
            url="https://youtube.com/video",
            title="Title",
            transcript="First transcript",
            summary="Summary",
            main_points="Points",
        )
        updated_transcript = YouTubeVideo(
            id="two",
            url=original.url,
            title=original.title,
            transcript="Second transcript",
            summary=original.summary,
            main_points=original.main_points,
        )

        self.assertNotEqual(original, updated_transcript)
        self.assertEqual(original.compute_hash(), updated_transcript.compute_hash())
        self.assertNotEqual(original, object())

        for field in ("id", "url", "title", "transcript", "summary", "main_points"):
            with self.subTest(field=field):
                changed = YouTubeVideo(
                    id=original.id,
                    url=original.url,
                    title=original.title,
                    transcript=original.transcript,
                    summary=original.summary,
                    main_points=original.main_points,
                )
                setattr(changed, field, f"changed {field}")
                self.assertNotEqual(original, changed)

        for field in ("title", "url", "summary", "main_points"):
            with self.subTest(hash_field=field):
                changed = YouTubeVideo(
                    url=original.url,
                    title=original.title,
                    summary=original.summary,
                    main_points=original.main_points,
                )
                setattr(changed, field, f"changed {field}")
                self.assertNotEqual(original.compute_hash(), changed.compute_hash())


if __name__ == "__main__":
    unittest.main()
