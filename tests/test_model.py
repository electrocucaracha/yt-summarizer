from yt_summarizer.model import YouTubeVideo


def test_youtube_video_initialization():
    video = YouTubeVideo(
        id="1",
        url="https://www.youtube.com/watch?v=abc123",
        title="Test Title",
        transcript="Test Transcript",
        summary="Test Summary",
        main_points="Test Points",
    )

    assert video.id == "1"
    assert video.url == "https://www.youtube.com/watch?v=abc123"
    assert video.title == "Test Title"
    assert video.transcript == "Test Transcript"
    assert video.summary == "Test Summary"
    assert video.main_points == "Test Points"


def test_youtube_video_repr():
    video = YouTubeVideo(
        id="1",
        url="https://www.youtube.com/watch?v=abc123",
        title="Test Title",
        transcript="Test Transcript",
        summary="Test Summary",
        main_points="Test Points",
    )

    repr_str = repr(video)
    assert "YouTubeVideo" in repr_str
    assert "Test Title" in repr_str
