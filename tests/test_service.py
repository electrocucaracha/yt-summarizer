"""Tests for the YouTube summarizer service module."""

from unittest.mock import Mock, patch

from yt_summarizer.model import YouTubeVideo
from yt_summarizer.service import YouTubeSummarizerService


class TestYouTubeSummarizerService:
    """Test cases for YouTubeSummarizerService class."""

    def _setup_mocks(self, mock_llm_client, mock_notion_client, mock_youtube_client, videos_data):
        """Helper to setup common mocks for tests."""
        mock_notion_instance = Mock()
        mock_notion_client.return_value = mock_notion_instance
        mock_notion_instance.get_page_properties_from_database.return_value = videos_data

        mock_llm_instance = Mock()
        mock_llm_client.return_value = mock_llm_instance
        mock_llm_instance.summarize.return_value = "Summary"
        mock_llm_instance.get_main_points.return_value = "Points"

        mock_yt_instance = Mock()
        mock_youtube_client.return_value = mock_yt_instance
        mock_yt_instance.get_video_title.return_value = "Title"
        mock_yt_instance.get_video_transcript.return_value = "Transcript"

        return mock_yt_instance

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
    def test_init_default_model(
        self,
        mock_llm_client,
        mock_notion_client,  # pylint: disable=unused-argument
    ):
        """Test service initialization with default model."""
        token = "test-token"

        _ = YouTubeSummarizerService(token=token)

        mock_llm_client.assert_called_once_with(
            model="ollama/llama3.2", api_base="http://localhost:11434"
        )

    @patch("yt_summarizer.service.YouTubeClient")
    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_get_videos_success(self, mock_llm_client, mock_notion_client, mock_youtube_client):
        """Test successful video retrieval and processing."""
        # Setup mock Notion client
        videos_data = [
            {
                "ID": "page-1",
                "URL": "https://www.youtube.com/watch?v=abc123",
                "Title": "",
                "Summary": None,
                "Main points": None,
            }
        ]

        self._setup_mocks(mock_llm_client, mock_notion_client, mock_youtube_client, videos_data)

        service = YouTubeSummarizerService(token="test-token")
        videos = service.get_videos("db-123")

        assert len(videos) == 1
        assert videos[0].id == "page-1"
        assert videos[0].title == "Title"
        assert videos[0].summary == "Summary"
        assert videos[0].main_points == "Points"

    @patch("yt_summarizer.service.YouTubeClient")
    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_get_videos_skip_no_url(self, mock_llm_client, mock_notion_client, mock_youtube_client):
        """Test that records without URLs are skipped."""
        videos_data = [
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

        self._setup_mocks(mock_llm_client, mock_notion_client, mock_youtube_client, videos_data)

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
        videos_data = [
            {
                "ID": "page-1",
                "URL": "https://www.youtube.com/watch?v=abc123",
                "Title": "Existing Title",
                "Summary": None,
                "Main points": None,
            }
        ]

        mock_yt_instance = self._setup_mocks(
            mock_llm_client, mock_notion_client, mock_youtube_client, videos_data
        )

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
        videos_data = [
            {
                "ID": "page-1",
                "URL": "https://www.youtube.com/watch?v=abc123",
                "Title": "Title",
                "Summary": "Existing summary",
                "Main points": "Existing points",
            }
        ]

        mock_yt_instance = self._setup_mocks(
            mock_llm_client, mock_notion_client, mock_youtube_client, videos_data
        )

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
        videos_data = [
            {
                "ID": "page-1",
                "URL": "https://www.youtube.com/watch?v=abc123",
                "Title": "Title",
                "Summary": None,
                "Main points": None,
            }
        ]

        self._setup_mocks(mock_llm_client, mock_notion_client, mock_youtube_client, videos_data)
        mock_llm_client.return_value.summarize.return_value = "Generated summary"
        mock_llm_client.return_value.get_main_points.return_value = "Generated points"
        mock_youtube_client.return_value.get_video_transcript.return_value = (
            "Sample transcript text"
        )

        service = YouTubeSummarizerService(token="test-token")
        videos = service.get_videos("db-123")

        assert videos[0].summary == "Generated summary"
        mock_llm_client.return_value.summarize.assert_called_once_with("Sample transcript text")

    @patch("yt_summarizer.service.YouTubeClient")
    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_get_videos_generates_main_points_when_missing(
        self, mock_llm_client, mock_notion_client, mock_youtube_client
    ):
        """Test that main points are generated when missing from Notion."""
        videos_data = [
            {
                "ID": "page-1",
                "URL": "https://www.youtube.com/watch?v=abc123",
                "Title": "Title",
                "Summary": "Existing summary",
                "Main points": None,
            }
        ]

        self._setup_mocks(mock_llm_client, mock_notion_client, mock_youtube_client, videos_data)
        mock_llm_client.return_value.get_main_points.return_value = "Generated main points"
        mock_youtube_client.return_value.get_video_transcript.return_value = (
            "Sample transcript text"
        )

        service = YouTubeSummarizerService(token="test-token")
        videos = service.get_videos("db-123")

        assert videos[0].main_points == "Generated main points"
        mock_llm_client.return_value.get_main_points.assert_called_once_with(
            "Sample transcript text"
        )

    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_update_video(
        self,
        mock_llm_client,
        mock_notion_client,  # pylint: disable=unused-argument
    ):
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
        videos_data = [
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

        self._setup_mocks(mock_llm_client, mock_notion_client, mock_youtube_client, videos_data)

        service = YouTubeSummarizerService(token="test-token")
        videos = service.get_videos("db-123")

        assert len(videos) == 3
        assert videos[0].id == "page-1"
        assert videos[1].id == "page-2"
        assert videos[2].id == "page-3"

    @patch("yt_summarizer.service.YouTubeClient")
    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_updated_flag_false_when_all_data_present(
        self, mock_llm_client, mock_notion_client, mock_youtube_client
    ):
        """Test that updated flag is False when all data already exists."""
        videos_data = [
            {
                "ID": "page-1",
                "URL": "https://www.youtube.com/watch?v=abc123",
                "Title": "Existing Title",
                "Transcript": "Existing Transcript",
                "Summary": "Existing Summary",
                "Main points": "Existing Points",
            }
        ]

        self._setup_mocks(mock_llm_client, mock_notion_client, mock_youtube_client, videos_data)

        service = YouTubeSummarizerService(token="test-token")
        videos = service.get_videos("db-123")

        assert videos[0].updated is False
        # No API calls should be made when all data exists
        mock_youtube_client.return_value.get_video_title.assert_not_called()
        mock_youtube_client.return_value.get_video_transcript.assert_not_called()
        mock_llm_client.return_value.summarize.assert_not_called()
        mock_llm_client.return_value.get_main_points.assert_not_called()

    @patch("yt_summarizer.service.YouTubeClient")
    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_updated_flag_true_when_title_fetched(
        self, mock_llm_client, mock_notion_client, mock_youtube_client
    ):
        """Test that updated flag is True when title is fetched from YouTube."""
        videos_data = [
            {
                "ID": "page-1",
                "URL": "https://www.youtube.com/watch?v=abc123",
                "Title": "",  # Missing title
                "Summary": "Existing Summary",
                "Main points": "Existing Points",
            }
        ]

        mock_yt_instance = self._setup_mocks(
            mock_llm_client, mock_notion_client, mock_youtube_client, videos_data
        )
        mock_yt_instance.get_video_title.return_value = "Fetched Title"

        service = YouTubeSummarizerService(token="test-token")
        videos = service.get_videos("db-123")

        assert videos[0].updated is True
        assert videos[0].title == "Fetched Title"
        mock_yt_instance.get_video_title.assert_called_once()
        # Transcript should not be fetched if summary and main_points exist
        mock_yt_instance.get_video_transcript.assert_not_called()

    @patch("yt_summarizer.service.YouTubeClient")
    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_updated_flag_true_when_summary_generated(
        self, mock_llm_client, mock_notion_client, mock_youtube_client
    ):
        """Test that updated flag is True when summary is generated."""
        videos_data = [
            {
                "ID": "page-1",
                "URL": "https://www.youtube.com/watch?v=abc123",
                "Title": "Existing Title",
                "Summary": None,  # Missing summary
                "Main points": "Existing Points",
            }
        ]

        mock_yt_instance = self._setup_mocks(
            mock_llm_client, mock_notion_client, mock_youtube_client, videos_data
        )
        mock_yt_instance.get_video_transcript.return_value = "Sample transcript"
        mock_llm_client.return_value.summarize.return_value = "Generated Summary"

        service = YouTubeSummarizerService(token="test-token")
        videos = service.get_videos("db-123")

        assert videos[0].updated is True
        assert videos[0].summary == "Generated Summary"
        mock_yt_instance.get_video_transcript.assert_called()
        mock_llm_client.return_value.summarize.assert_called_once()
        # Main points should not be re-generated since they exist
        mock_llm_client.return_value.get_main_points.assert_not_called()

    @patch("yt_summarizer.service.YouTubeClient")
    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_updated_flag_true_when_main_points_generated(
        self, mock_llm_client, mock_notion_client, mock_youtube_client
    ):
        """Test that updated flag is True when main points are generated."""
        videos_data = [
            {
                "ID": "page-1",
                "URL": "https://www.youtube.com/watch?v=abc123",
                "Title": "Existing Title",
                "Summary": "Existing Summary",
                "Main points": None,  # Missing main points
            }
        ]

        mock_yt_instance = self._setup_mocks(
            mock_llm_client, mock_notion_client, mock_youtube_client, videos_data
        )
        mock_yt_instance.get_video_transcript.return_value = "Sample transcript"
        mock_llm_client.return_value.get_main_points.return_value = "Generated Main Points"

        service = YouTubeSummarizerService(token="test-token")
        videos = service.get_videos("db-123")

        assert videos[0].updated is True
        assert videos[0].main_points == "Generated Main Points"
        mock_yt_instance.get_video_transcript.assert_called()
        mock_llm_client.return_value.get_main_points.assert_called_once()
        # Summary should not be re-generated since it exists
        mock_llm_client.return_value.summarize.assert_not_called()

    @patch("yt_summarizer.service.YouTubeClient")
    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_updated_flag_true_when_multiple_fields_missing(
        self, mock_llm_client, mock_notion_client, mock_youtube_client
    ):
        """Test updated flag is True when multiple fields are missing."""
        videos_data = [
            {
                "ID": "page-1",
                "URL": "https://www.youtube.com/watch?v=abc123",
                "Title": "",  # Missing title
                "Summary": None,  # Missing summary
                "Main points": None,  # Missing main points
            }
        ]

        mock_yt_instance = self._setup_mocks(
            mock_llm_client, mock_notion_client, mock_youtube_client, videos_data
        )
        mock_yt_instance.get_video_title.return_value = "Fetched Title"
        mock_yt_instance.get_video_transcript.return_value = "Sample transcript"
        mock_llm_client.return_value.summarize.return_value = "Generated Summary"
        mock_llm_client.return_value.get_main_points.return_value = "Generated Main Points"

        service = YouTubeSummarizerService(token="test-token")
        videos = service.get_videos("db-123")

        assert videos[0].updated is True
        assert videos[0].title == "Fetched Title"
        assert videos[0].summary == "Generated Summary"
        assert videos[0].main_points == "Generated Main Points"

    @patch("yt_summarizer.service.YouTubeClient")
    @patch("yt_summarizer.service.NotionClient")
    @patch("yt_summarizer.service.LLMClient")
    def test_transcript_reuse_when_both_summary_and_main_points_missing(
        self, mock_llm_client, mock_notion_client, mock_youtube_client
    ):
        """Test that transcript is fetched once and reused for both summary and main_points."""
        videos_data = [
            {
                "ID": "page-1",
                "URL": "https://www.youtube.com/watch?v=abc123",
                "Title": "Existing Title",
                "Summary": None,  # Missing summary
                "Main points": None,  # Missing main points
            }
        ]

        mock_yt_instance = self._setup_mocks(
            mock_llm_client, mock_notion_client, mock_youtube_client, videos_data
        )
        mock_yt_instance.get_video_transcript.return_value = "Sample transcript"
        mock_llm_client.return_value.summarize.return_value = "Generated Summary"
        mock_llm_client.return_value.get_main_points.return_value = "Generated Main Points"

        service = YouTubeSummarizerService(token="test-token")
        videos = service.get_videos("db-123")

        assert videos[0].updated is True
        # Transcript should be fetched only once, not twice
        assert mock_yt_instance.get_video_transcript.call_count == 1
        # Both LLM methods should be called with same transcript
        mock_llm_client.return_value.summarize.assert_called_once_with("Sample transcript")
        mock_llm_client.return_value.get_main_points.assert_called_once_with("Sample transcript")
