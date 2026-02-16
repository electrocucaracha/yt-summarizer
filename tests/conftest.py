"""Shared pytest configuration and fixtures."""

import pytest


@pytest.fixture
def youtube_url():
    """Standard YouTube URL for testing."""
    return "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture
def video_id():
    """Standard video ID for testing."""
    return "dQw4w9WgXcQ"


@pytest.fixture
def sample_transcript():
    """Sample transcript text for testing."""
    return (
        "This is a sample transcript. It contains multiple sentences. "
        "Each sentence provides some information. The transcript is used for testing. "
        "We can generate summaries and extract main points from it."
    )


@pytest.fixture
def sample_summary():
    """Sample LLM-generated summary."""
    return (
        "This is a concise summary of the video content. "
        "It contains the key information from the transcript in shortened form."
    )


@pytest.fixture
def sample_main_points():
    """Sample LLM-extracted main points."""
    return (
        "• Point 1: First key takeaway\n"
        "• Point 2: Second key takeaway\n"
        "• Point 3: Third key takeaway"
    )


@pytest.fixture
def mock_youtube_response_html(video_id):
    """Mock HTML response from YouTube page."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta property="og:title" content="Sample Video Title">
    </head>
    <body>
        <script>window.ytInitialData = {}</script>
    </body>
    </html>
    """
