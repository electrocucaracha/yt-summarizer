import unittest

from yt_summarizer.model import YouTubeVideo


class TestYouTubeVideo(unittest.TestCase):

    def test_video_initialization(self):
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


if __name__ == "__main__":
    unittest.main()
