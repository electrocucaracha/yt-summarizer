import unittest
from unittest.mock import MagicMock

from yt_summarizer.model import YouTubeVideo
from yt_summarizer.service import YouTubeSummarizerService


def test_get_videos_from_notion_db():
    notion_client_mock = MagicMock()
    notion_client_mock.get_page_properties_from_database.return_value = [
        {
            "ID": "1",
            "URL": "https://www.youtube.com/watch?v=abc123",
            "Title": "Test Video",
            "Transcript": "Test Transcript",
            "Summary": "Test Summary",
            "Main points": "Test Points",
        }
    ]

    service = YouTubeSummarizerService(token="dummy_token")
    service.notion_client = notion_client_mock

    videos = service.get_videos_from_notion_db("dummy_db_id")

    assert len(videos) == 1
    video = videos[0]
    assert video.id == "1"
    assert video.url == "https://www.youtube.com/watch?v=abc123"
    assert video.title == "Test Video"
    assert video.transcript == "Test Transcript"
    assert video.summary == "Test Summary"
    assert video.main_points == "Test Points"


def test_process_video():
    youtube_client_mock = MagicMock()
    youtube_client_mock.get_video_title.return_value = "Mock Title"
    youtube_client_mock.get_video_transcript.return_value = "Mock Transcript"

    llm_client_mock = MagicMock()
    llm_client_mock.summarize.return_value = "Mock Summary"
    llm_client_mock.get_main_points.return_value = "Mock Points"

    service = YouTubeSummarizerService(token="dummy_token")
    service.youtube_client = youtube_client_mock
    service.llm_client = llm_client_mock

    video = YouTubeVideo(id="1", url="https://www.youtube.com/watch?v=abc123")
    processed_video = service.process_video(video)

    assert processed_video.title == "Mock Title"
    assert processed_video.summary == "Mock Summary"
    assert processed_video.main_points == "Mock Points"


def test_update_video():
    notion_client_mock = MagicMock()

    service = YouTubeSummarizerService(token="dummy_token")
    service.notion_client = notion_client_mock

    video = YouTubeVideo(
        id="1",
        url="https://www.youtube.com/watch?v=abc123",
        title="Updated Title",
        summary="Updated Summary",
        main_points="Updated Points",
    )

    service.update_video("dummy_db_id", video)

    notion_client_mock.update_page_properties.assert_called_once_with(
        "dummy_db_id",
        "1",
        {
            "Title": "Updated Title",
            "Summary": "Updated Summary",
            "Main Points": "Updated Points",
        },
    )


def test_upsert_video():
    notion_client_mock = MagicMock()
    notion_client_mock.get_page_properties_from_database.return_value = [
        {
            "ID": "1",
            "URL": "https://www.youtube.com/watch?v=abc123",
            "Title": "Test Video",
            "Summary": "Test Summary",
            "Main Points": "Test Points",
        }
    ]

    service = YouTubeSummarizerService(token="dummy_token")
    service.notion_client = notion_client_mock

    video = YouTubeVideo(
        id="1",
        url="https://www.youtube.com/watch?v=abc123",
        title="Updated Title",
        summary="Updated Summary",
        main_points="Updated Points",
    )

    service.upsert_video("dummy_db_id", video)

    notion_client_mock.update_page_properties.assert_called_once_with(
        "dummy_db_id",
        "1",
        {
            "Title": "Updated Title",
            "URL": "https://www.youtube.com/watch?v=abc123",
            "Summary": "Updated Summary",
            "Main Points": "Updated Points",
        },
    )


def test_get_video_by_url():
    notion_client_mock = MagicMock()
    notion_client_mock.get_page_properties_from_database.return_value = [
        {
            "ID": "1",
            "URL": "https://www.youtube.com/watch?v=abc123",
            "Title": "Test Video",
            "Transcript": "Test Transcript",
            "Summary": "Test Summary",
            "Main points": "Test Points",
        }
    ]

    service = YouTubeSummarizerService(token="dummy_token")
    service.notion_client = notion_client_mock

    video = service.get_video_by_url(
        "dummy_db_id", "https://www.youtube.com/watch?v=abc123"
    )

    assert video.id == "1"
    assert video.url == "https://www.youtube.com/watch?v=abc123"
    assert video.title == "Test Video"
    assert video.summary == "Test Summary"
    assert video.main_points == "Test Points"


def test_get_videos_from_playlist():
    youtube_dl_mock = MagicMock()
    youtube_dl_mock.return_value.__enter__.return_value.extract_info.return_value = {
        "entries": [
            {
                "id": "abc123",
                "title": "Test Video",
            }
        ]
    }

    service = YouTubeSummarizerService(token="dummy_token")

    with unittest.mock.patch("yt_dlp.YoutubeDL", youtube_dl_mock):
        videos = service.get_videos_from_playlist(
            "https://www.youtube.com/playlist?list=PL123"
        )

    assert len(videos) == 1
    video = videos[0]
    assert video.id == "abc123"
    assert video.url == "https://www.youtube.com/watch?v=abc123"
    assert video.title == "Test Video"
