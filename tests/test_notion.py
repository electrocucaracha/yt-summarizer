"""Tests for the Notion client module."""

import unittest
from unittest.mock import MagicMock

from yt_summarizer.notion import Client


class TestNotionClient(unittest.TestCase):
    """Tests for the Notion Client class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_token = "mock_token"
        self.mock_http_client = MagicMock()
        self.client = Client(token=self.mock_token, client=self.mock_http_client)
        self.client.notion_client = MagicMock()

    def test_initialization(self):
        """Test that the Notion client initializes with the correct attributes."""
        self.assertIsNotNone(self.client.notion_client)

    def test_get_page_properties_from_database_uses_data_source_query(self):
        """Test that database reads use the data source query endpoint."""
        self.client.notion_client.databases.retrieve.return_value = {
            "id": "database-id",
            "data_sources": [{"id": "data-source-id"}],
        }
        self.client.notion_client.data_sources.query.return_value = {
            "results": [
                {
                    "id": "page-1",
                    "properties": {
                        "URL": {"type": "url", "url": "https://example.com/video"},
                        "Published": {"type": "checkbox", "checkbox": True},
                    },
                }
            ],
            "has_more": False,
            "next_cursor": None,
        }

        properties = self.client.get_page_properties_from_database("database-id")

        self.client.notion_client.data_sources.query.assert_called_once_with(
            data_source_id="data-source-id",
            page_size=100,
            result_type="page",
        )
        self.client.notion_client.pages.retrieve.assert_not_called()
        self.assertEqual(
            [{"URL": "https://example.com/video", "Published": True, "ID": "page-1"}],
            properties,
        )

    def test_get_page_properties_from_database_paginates_data_source_results(self):
        """Test that data source pagination is followed until all pages are retrieved."""
        self.client.notion_client.databases.retrieve.return_value = {
            "id": "database-id",
            "data_sources": [{"id": "data-source-id"}],
        }
        self.client.notion_client.data_sources.query.side_effect = [
            {
                "results": [
                    {
                        "id": "page-1",
                        "properties": {
                            "URL": {"type": "url", "url": "https://example.com/1"}
                        },
                    }
                ],
                "has_more": True,
                "next_cursor": "cursor-1",
            },
            {
                "results": [
                    {
                        "id": "page-2",
                        "properties": {
                            "URL": {"type": "url", "url": "https://example.com/2"}
                        },
                    }
                ],
                "has_more": False,
                "next_cursor": None,
            },
        ]

        properties = self.client.get_page_properties_from_database("database-id")

        self.assertEqual(2, len(properties))
        self.assertEqual(
            [
                {
                    "data_source_id": "data-source-id",
                    "page_size": 100,
                    "result_type": "page",
                },
                {
                    "data_source_id": "data-source-id",
                    "page_size": 100,
                    "result_type": "page",
                    "start_cursor": "cursor-1",
                },
            ],
            [
                call.kwargs
                for call in self.client.notion_client.data_sources.query.call_args_list
            ],
        )

    def test_get_page_properties_from_database_falls_back_without_data_source(self):
        """Test that database reads fall back when the database has no data source."""
        self.client.notion_client.databases.retrieve.return_value = {
            "id": "database-id",
            "properties": {},
        }
        self.client.get_database_content = MagicMock(return_value=[{"id": "page-1"}])
        self.client.get_page_properties = MagicMock(
            return_value={"URL": "https://example.com/video"}
        )

        properties = self.client.get_page_properties_from_database("database-id")

        self.client.get_database_content.assert_called_once_with("database-id")
        self.client.get_page_properties.assert_called_once_with("page-1")
        self.client.notion_client.data_sources.query.assert_not_called()
        self.assertEqual(
            [{"URL": "https://example.com/video", "ID": "page-1"}], properties
        )


if __name__ == "__main__":
    unittest.main()
