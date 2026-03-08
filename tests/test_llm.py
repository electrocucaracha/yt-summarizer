from unittest.mock import MagicMock

import pytest

from yt_summarizer.llm import Client


def test_summarize():
    litellm_mock = MagicMock()
    litellm_mock.completion.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Mock Summary"))]
    )

    client = Client(model="mock_model", api_base="http://mock-api")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("yt_summarizer.llm.litellm", litellm_mock)
        summary = client.summarize("Mock Transcript")

    assert summary == "Mock Summary"
    litellm_mock.completion.assert_called_once()
