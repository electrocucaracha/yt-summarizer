# Unit Tests for YouTube Summarizer

This directory contains comprehensive unit tests for the YouTube Summarizer application.

## Test Structure

- **test_model.py**: Tests for the `YouTubeVideo` data model
- **test_youtube.py**: Tests for YouTube client functionality (metadata and transcript extraction)
- **test_llm.py**: Tests for LLM client functionality (summarization and main points extraction)
- **test_notion.py**: Tests for Notion database client functionality
- **test_service.py**: Tests for the main orchestration service
- **test_cli.py**: Tests for the CLI entry point
- **conftest.py**: Shared fixtures and test utilities

## Running Tests

### Run all tests
```bash
pytest
```

### Run tests with coverage report
```bash
pytest --cov=src/yt_summarizer --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_model.py
```

### Run specific test class
```bash
pytest tests/test_model.py::TestYouTubeVideo
```

### Run specific test
```bash
pytest tests/test_model.py::TestYouTubeVideo::test_init_with_all_fields
```

### Run tests with verbose output
```bash
pytest -v
```

### Run tests with different log levels
```bash
pytest -v --log-cli-level=DEBUG
```

## Test Coverage

To generate a coverage report:

```bash
pytest --cov=src/yt_summarizer --cov-report=html
```

This will generate an HTML report in `htmlcov/index.html`.

## Fixtures

Common fixtures are defined in `conftest.py`:

- `youtube_url`: Standard YouTube URL for testing
- `video_id`: Standard video ID for testing
- `sample_transcript`: Sample transcript text
- `sample_summary`: Sample LLM-generated summary
- `sample_main_points`: Sample LLM-extracted main points
- `mock_youtube_response_html`: Mock HTML response from YouTube

## Mocking Strategy

The tests use `pytest-mock` and `unittest.mock` to mock external dependencies:

- **YouTube API**: Mocked to avoid real API calls during testing
- **Notion API**: Mocked to avoid database modifications during testing
- **LLM API**: Mocked to avoid model inference during testing
- **HTTP requests**: Mocked to control HTML responses

This allows tests to run quickly and reliably without depending on external services.

## Adding New Tests

When adding new tests:

1. Follow the existing test structure: `test_<module_name>.py`
2. Use descriptive test names: `test_<functionality>_<scenario>`
3. Use appropriate fixtures from `conftest.py`
4. Mock all external dependencies
5. Include tests for both success and error cases
6. Add docstrings explaining what the test verifies
