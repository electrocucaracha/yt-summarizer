"""Tests for the YouTube summarizer service module."""

from unittest.mock import Mock, patch

from yt_summarizer.model import YouTubeVideo
from yt_summarizer.service import YouTubeSummarizerService


class TestYouTubeSummarizerService:
    """Test cases for YouTubeSummarizerService class."""

    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_init(self, mock_llm_client, mock_notion_client):
        """Test service initialization."""
        token = "test-notion-token"
        model = "ollama/llama3.2"
        api_base = "http://localhost:11434"

        service = YouTubeSummarizerService(token=token, model=model, api_base=api_base)

        mock_notion_client.assert_called_once_with(token=token)
        mock_llm_client.assert_called_once_with(model=model, api_base=api_base)
        assert service.notion_client is not None
        assert service.llm_client is not None

    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_init_default_model(self, mock_llm_client, mock_notion_client):
        """Test service initialization with default model."""
        token = "test-token"

        _ = YouTubeSummarizerService(token=token)

        mock_llm_client.assert_called_once_with(
            model="ollama/llama3.2", api_base="http://localhost:11434"
        )

    @patch("yt_summarizer.service.YouTubeClient")
    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_get_videos_success(
        self, mock_llm_client, mock_notion_client, mock_youtube_client
    ):
        """Test successful video retrieval and processing."""
        # Setup mock Notion client
        mock_notion_instance = Mock()
        mock_notion_client.return_value = mock_notion_instance
        mock_notion_instance.get_page_properties_from_database.return_value = [
            {
                "ID": "page-1",
                "URL": "https://www.youtube.com/watch?v=abc123",
                "Title": "",
                "Summary": None,
                "Main points": None,
            }
        ]

        # Setup mock LLM client
        mock_llm_instance = Mock()
        mock_llm_client.return_value = mock_llm_instance
        mock_llm_instance.summarize.return_value = "Summary of video"
        mock_llm_instance.get_main_points.return_value = "• Point 1\n• Point 2"

        # Setup mock YouTube client
        mock_yt_instance = Mock()
        mock_youtube_client.return_value = mock_yt_instance
        mock_yt_instance.get_video_title.return_value = "Video Title"
        mock_yt_instance.get_video_transcript.return_value = "Video transcript text"

        service = YouTubeSummarizerService(token="test-token")
        videos = service.get_videos("db-123")

        assert len(videos) == 1
        assert videos[0].id == "page-1"
        assert videos[0].title == "Video Title"
        assert videos[0].summary == "Summary of video"
        assert videos[0].main_points == "• Point 1\n• Point 2"
        # Verify YouTube API was called to fetch transcript
        mock_yt_instance.get_video_transcript.assert_called()

    @patch("yt_summarizer.service.YouTubeClient")
    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_get_videos_skip_no_url(
        self, mock_llm_client, mock_notion_client, mock_youtube_client
    ):
        """Test that records without URLs are skipped."""
        mock_notion_instance = Mock()
        mock_notion_client.return_value = mock_notion_instance
        mock_notion_instance.get_page_properties_from_database.return_value = [
            {
                "ID": "page-1",
                "URL": "",  # No URL
                "Title": "Title 1",
                "Summary": None,
                "Main points": None,
            },
            {
                "ID": "page-2",
                "URL": "https://www.youtube.com/watch?v=xyz789",
                "Title": "",
                "Summary": None,
                "Main points": None,
            },
        ]

        mock_llm_instance = Mock()
        mock_llm_client.return_value = mock_llm_instance
        mock_llm_instance.summarize.return_value = "Summary"
        mock_llm_instance.get_main_points.return_value = "Points"

        mock_yt_instance = Mock()
        mock_youtube_client.return_value = mock_yt_instance
        mock_yt_instance.get_video_title.return_value = "Title"
        mock_yt_instance.get_video_transcript.return_value = "Transcript"

        service = YouTubeSummarizerService(token="test-token")
        videos = service.get_videos("db-123")

        assert len(videos) == 1
        assert videos[0].id == "page-2"

    @patch("yt_summarizer.service.YouTubeClient")
    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_get_videos_uses_existing_title(
        self, mock_llm_client, mock_notion_client, mock_youtube_client
    ):
        """Test that existing title is not overwritten."""
        mock_notion_instance = Mock()
        mock_notion_client.return_value = mock_notion_instance
        mock_notion_instance.get_page_properties_from_database.return_value = [
            {
                "ID": "page-1",
                "URL": "https://www.youtube.com/watch?v=abc123",
                "Title": "Existing Title",
                "Summary": None,
                "Main points": None,
            }
        ]

        mock_llm_instance = Mock()
        mock_llm_client.return_value = mock_llm_instance
        mock_llm_instance.summarize.return_value = "Summary"
        mock_llm_instance.get_main_points.return_value = "Points"

        mock_yt_instance = Mock()
        mock_youtube_client.return_value = mock_yt_instance
        mock_yt_instance.get_video_transcript.return_value = "Fetched transcript"

        service = YouTubeSummarizerService(token="test-token")
        videos = service.get_videos("db-123")

        assert videos[0].title == "Existing Title"
        # Should not call YouTube API for title if it exists
        mock_yt_instance.get_video_title.assert_not_called()

    @patch("yt_summarizer.service.YouTubeClient")
    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_get_videos_skip_when_summary_and_points_exist(
        self, mock_llm_client, mock_notion_client, mock_youtube_client
    ):
        """Test that YouTube API is not called when summary and main_points already exist."""
        mock_notion_instance = Mock()
        mock_notion_client.return_value = mock_notion_instance
        mock_notion_instance.get_page_properties_from_database.return_value = [
            {
                "ID": "page-1",
                "URL": "https://www.youtube.com/watch?v=abc123",
                "Title": "Title",
                "Summary": "Existing summary",
                "Main points": "Existing points",
            }
        ]

        mock_llm_instance = Mock()
        mock_llm_client.return_value = mock_llm_instance

        mock_yt_instance = Mock()
        mock_youtube_client.return_value = mock_yt_instance

        service = YouTubeSummarizerService(token="test-token")
        videos = service.get_videos("db-123")

        assert videos[0].summary == "Existing summary"
        assert videos[0].main_points == "Existing points"
        # Should not call YouTube API if summary and main_points already exist
        mock_yt_instance.get_video_transcript.assert_not_called()

    @patch("yt_summarizer.service.YouTubeClient")
    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_get_videos_generates_summary_when_missing(
        self, mock_llm_client, mock_notion_client, mock_youtube_client
    ):
        """Test that summary is generated when missing from Notion."""
        mock_notion_instance = Mock()
        mock_notion_client.return_value = mock_notion_instance
        mock_notion_instance.get_page_properties_from_database.return_value = [
            {
                "ID": "page-1",
                "URL": "https://www.youtube.com/watch?v=abc123",
                "Title": "Title",
                "Summary": None,
                "Main points": None,
            }
        ]

        mock_llm_instance = Mock()
        mock_llm_client.return_value = mock_llm_instance
        mock_llm_instance.summarize.return_value = "Generated summary"
        mock_llm_instance.get_main_points.return_value = "Generated points"

        mock_yt_instance = Mock()
        mock_youtube_client.return_value = mock_yt_instance
        mock_yt_instance.get_video_transcript.return_value = "Sample transcript text"

        service = YouTubeSummarizerService(token="test-token")
        videos = service.get_videos("db-123")

        assert videos[0].summary == "Generated summary"
        mock_llm_instance.summarize.assert_called_once_with("Sample transcript text")

    @patch("yt_summarizer.service.YouTubeClient")
    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_get_videos_generates_main_points_when_missing(
        self, mock_llm_client, mock_notion_client, mock_youtube_client
    ):
        """Test that main points are generated when missing from Notion."""
        mock_notion_instance = Mock()
        mock_notion_client.return_value = mock_notion_instance
        mock_notion_instance.get_page_properties_from_database.return_value = [
            {
                "ID": "page-1",
                "URL": "https://www.youtube.com/watch?v=abc123",
                "Title": "Title",
                "Summary": "Existing summary",
                "Main points": None,
            }
        ]

        mock_llm_instance = Mock()
        mock_llm_client.return_value = mock_llm_instance
        mock_llm_instance.get_main_points.return_value = "Generated main points"

        mock_yt_instance = Mock()
        mock_youtube_client.return_value = mock_yt_instance
        mock_yt_instance.get_video_transcript.return_value = "Sample transcript text"

        service = YouTubeSummarizerService(token="test-token")
        videos = service.get_videos("db-123")

        assert videos[0].main_points == "Generated main points"
        mock_llm_instance.get_main_points.assert_called_once_with(
            "Sample transcript text"
        )

    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_update_video(self, mock_llm_client, mock_notion_client):
        """Test updating a video record in the database."""
        mock_notion_instance = Mock()
        mock_notion_client.return_value = mock_notion_instance

        video = YouTubeVideo(
            id="page-1",
            url="https://www.youtube.com/watch?v=abc123",
            title="Video Title",
            transcript="Transcript",
            summary="Summary",
            main_points="Main Points",
        )

        service = YouTubeSummarizerService(token="test-token")
        service.update_video("db-123", video)

        mock_notion_instance.update_page_properties.assert_called_once_with(
            "db-123",
            "page-1",
            {
                "Title": "Video Title",
                "Summary": "Summary",
                "Main Points": "Main Points",
            },
        )

    @patch("yt_summarizer.service.YouTubeClient")
    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_get_videos_multiple_records(
        self, mock_llm_client, mock_notion_client, mock_youtube_client
    ):
        """Test processing multiple video records."""
        mock_notion_instance = Mock()
        mock_notion_client.return_value = mock_notion_instance
        mock_notion_instance.get_page_properties_from_database.return_value = [
            {
                "ID": "page-1",
                "URL": "https://www.youtube.com/watch?v=vid1",
                "Title": "",
                "Summary": None,
                "Main points": None,
            },
            {
                "ID": "page-2",
                "URL": "https://www.youtube.com/watch?v=vid2",
                "Title": "",
                "Summary": None,
                "Main points": None,
            },
            {
                "ID": "page-3",
                "URL": "https://www.youtube.com/watch?v=vid3",
                "Title": "",
                "Summary": None,
                "Main points": None,
            },
        ]

        mock_llm_instance = Mock()
        mock_llm_client.return_value = mock_llm_instance
        mock_llm_instance.summarize.return_value = "Summary"
        mock_llm_instance.get_main_points.return_value = "Points"

        mock_yt_instance = Mock()
        mock_youtube_client.return_value = mock_yt_instance
        mock_yt_instance.get_video_title.return_value = "Title"
        mock_yt_instance.get_video_transcript.return_value = "Transcript"

        service = YouTubeSummarizerService(token="test-token")
        videos = service.get_videos("db-123")

        assert len(videos) == 3
        assert videos[0].id == "page-1"
        assert videos[1].id == "page-2"
        assert videos[2].id == "page-3"
