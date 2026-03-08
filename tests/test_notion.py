from unittest.mock import MagicMock

from yt_summarizer.notion import Client


def test_notion_client_initialization():
    notion_client_mock = MagicMock()
    client = Client(token="mock_token", client=notion_client_mock)

    assert client.client == notion_client_mock


def test_user_to_string():
    notion_client_mock = MagicMock()
    client = Client(token="mock_token", client=notion_client_mock)

    user = {"id": "123", "name": "Test User"}
    user_str = client._user_to_string(user)

    assert user_str == "123: Test User"
