"""Tests for the YouTubeVideo model."""

from yt_summarizer.model import YouTubeVideo


class TestYouTubeVideo:
    """Test cases for YouTubeVideo class."""

    def test_init_with_all_fields(self):
        """Test initialization with all fields provided."""
        video = YouTubeVideo(
            id="123",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title="Sample Title",
            transcript="Sample transcript",
            summary="Sample summary",
            main_points="Sample main points",
        )

        assert video.id == "123"
        assert video.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert video.title == "Sample Title"
        assert video.transcript == "Sample transcript"
        assert video.summary == "Sample summary"
        assert video.main_points == "Sample main points"

    def test_init_with_required_fields_only(self):
        """Test initialization with only required fields."""
        video = YouTubeVideo(
            id="123",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )

        assert video.id == "123"
        assert video.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert video.title == ""
        assert video.transcript == ""
        assert video.summary == ""
        assert video.main_points == ""

    def test_repr(self):
        """Test string representation of YouTubeVideo."""
        video = YouTubeVideo(
            id="123",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title="Sample Title",
            transcript="A" * 1000,
            summary="B" * 200,
            main_points="C" * 150,
        )

        repr_str = repr(video)
        assert "YouTubeVideo" in repr_str
        assert "Sample Title" in repr_str
        # Check that lengths are included
        assert "transcript_length=1000" in repr_str
        assert "summary_length=200" in repr_str
        assert "main_points_length=150" in repr_str

    def test_str(self):
        """Test human-readable string representation."""
        video = YouTubeVideo(
            id="123",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title="Sample Title",
            transcript="Sample transcript",
            summary="Sample summary",
            main_points="Sample main points",
        )

        str_repr = str(video)
        assert "URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ" in str_repr
        assert "Title: Sample Title" in str_repr
        assert "Transcript: Sample transcript" in str_repr
        assert "Summary: Sample summary" in str_repr
        assert "Main Points: Sample main points" in str_repr

    def test_empty_fields(self):
        """Test that empty fields are handled correctly."""
        video = YouTubeVideo(
            id="",
            url="",
            title="",
            transcript="",
            summary="",
            main_points="",
        )

        assert video.id == ""
        assert video.url == ""
        assert video.title == ""
        assert video.transcript == ""
        assert video.summary == ""
        assert video.main_points == ""

    def test_field_modification(self):
        """Test that fields can be modified after initialization."""
        video = YouTubeVideo(
            id="123",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )

        video.title = "New Title"
        video.transcript = "New transcript"
        video.summary = "New summary"
        video.main_points = "New main points"

        assert video.title == "New Title"
        assert video.transcript == "New transcript"
        assert video.summary == "New summary"
        assert video.main_points == "New main points"
