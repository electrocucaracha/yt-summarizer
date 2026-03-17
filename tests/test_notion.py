import unittest
from unittest.mock import MagicMock

from yt_summarizer.notion import Client


class TestNotionClient(unittest.TestCase):

    def setUp(self):
        self.mock_token = "mock_token"
        self.mock_http_client = MagicMock()
        self.client = Client(token=self.mock_token, client=self.mock_http_client)

    def test_initialization(self):
        self.assertEqual(self.client.token, self.mock_token)
        self.assertIsNotNone(self.client.notion_client)


if __name__ == "__main__":
    unittest.main()
