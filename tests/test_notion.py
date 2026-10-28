"""Tests for the Notion client module."""

import unittest
from datetime import datetime
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

    def test_extract_property_item_values(self):
        """Notion property types should be normalized to readable strings."""
        date = datetime(2024, 1, 2, 3, 4, 5)
        cases = [
            ({"type": "checkbox", "checkbox": True}, "True"),
            (
                {"type": "created_by", "created_by": {"id": "u1", "name": "Ada"}},
                "u1: Ada",
            ),
            (
                {"type": "created_time", "created_time": "2024-01-02T03:04:05"},
                date.isoformat(),
            ),
            ({"type": "date", "date": {"start": date}}, date.isoformat()),
            ({"type": "email", "email": "ada@example.com"}, "ada@example.com"),
            ({"type": "url", "url": "https://example.com"}, "https://example.com"),
            ({"type": "number", "number": 2.5}, "2.5"),
            ({"type": "phone_number", "phone_number": "123"}, "123"),
            ({"type": "select", "select": {"id": "s1", "name": "Ready"}}, "s1 Ready"),
            (
                {"type": "multi_select", "multi_select": [{"id": "s1", "name": "A"}]},
                "s1 A",
            ),
            ({"type": "people", "people": {"id": "u1", "name": "Ada"}}, "u1: Ada"),
            (
                {
                    "type": "last_edited_by",
                    "last_edited_by": {"id": "u1", "name": "Ada"},
                },
                "u1: Ada",
            ),
            ({"type": "last_edited_time", "last_edited_time": date}, date.isoformat()),
            ({"type": "title", "title": {"plain_text": "Title"}}, "Title"),
            ({"type": "rich_text", "rich_text": {"plain_text": "Text"}}, "Text"),
            (
                {"type": "files", "files": [{"name": "a.pdf"}, {"name": "b.pdf"}]},
                "a.pdf, b.pdf",
            ),
            (
                {"type": "formula", "formula": {"type": "string", "string": "text"}},
                "text",
            ),
            ({"type": "formula", "formula": {"type": "number", "number": 3}}, "3"),
            (
                {"type": "formula", "formula": {"type": "boolean", "boolean": False}},
                "False",
            ),
            (
                {
                    "type": "formula",
                    "formula": {"type": "date", "date": {"start": date}},
                },
                date.isoformat(),
            ),
            ({"type": "rollup", "rollup": {"type": "number", "number": 3}}, "3"),
            (
                {"type": "rollup", "rollup": {"type": "array", "array": [1, 2]}},
                "[1, 2]",
            ),
            ({"type": "rollup", "rollup": {"type": "unsupported"}}, "unsupported"),
            ({"type": "relation", "relation": {"id": "page-1"}}, "page-1"),
            ({"type": "status", "status": {"name": "Done"}}, "Done"),
            ({"type": "button", "button": {"name": "Run"}}, "Run"),
            (
                {"type": "unique_id", "unique_id": {"prefix": "TASK-", "number": 7}},
                "TASK-7",
            ),
            (
                {"type": "verification", "verification": {"state": "verified"}},
                "verified",
            ),
            ({"type": "unknown"}, ""),
        ]

        for item, expected in cases:
            with self.subTest(item=item):
                self.assertEqual(
                    expected, self.client._extract_property_item_value_to_string(item)
                )

    def test_extract_value_supports_property_items_and_lists(self):
        """Property item lists should be joined while unknown payloads stay empty."""
        self.assertEqual(
            "True, https://example.com",
            self.client._extract_value_to_string(
                {
                    "object": "list",
                    "results": [
                        {"type": "checkbox", "checkbox": True},
                        {"type": "url", "url": "https://example.com"},
                    ],
                }
            ),
        )
        self.assertEqual(
            "Title",
            self.client._extract_value_to_string(
                {
                    "object": "property_item",
                    "type": "title",
                    "title": {"plain_text": "Title"},
                }
            ),
        )
        self.assertEqual(
            "", self.client._extract_value_to_string({"object": "unknown"})
        )

    def test_format_property_for_update_supports_notion_types(self):
        """Supported values should be converted to the Notion API property shape."""
        cases = [
            ("title", "A title", {"title": [{"text": {"content": "A title"}}]}),
            ("checkbox", "yes", {"checkbox": True}),
            ("checkbox", "no", {"checkbox": False}),
            ("number", "4", {"number": 4}),
            ("number", "2.5", {"number": 2.5}),
            ("select", "Ready", {"select": {"name": "Ready"}}),
            (
                "multi_select",
                "one, two",
                {"multi_select": [{"name": "one"}, {"name": "two"}]},
            ),
            ("date", "2024-01-02", {"date": {"start": "2024-01-02"}}),
            ("url", "https://example.com", {"url": "https://example.com"}),
            ("email", "a@example.com", {"email": "a@example.com"}),
            ("phone_number", "123", {"phone_number": "123"}),
            ("status", "Done", {"status": {"name": "Done"}}),
        ]
        for prop_type, value, expected in cases:
            with self.subTest(prop_type=prop_type, value=value):
                self.assertEqual(
                    expected, self.client._format_property_for_update(prop_type, value)
                )

        self.assertEqual(
            {"rich_text": [{"type": "text", "text": {"content": "Text"}}]},
            self.client._format_property_for_update(
                "rich_text",
                '[{"type":"text","text":{"content":"Text"}}]',
            ),
        )
        self.assertIsNone(self.client._format_property_for_update("title", "[invalid]"))
        self.assertIsNone(self.client._format_property_for_update("number", "NaN?"))
        self.assertIsNone(
            self.client._format_property_for_update("unsupported", "value")
        )
        self.assertIsNone(self.client._format_property_for_update("title", "  "))
        self.assertEqual(
            2000,
            len(
                self.client._format_property_for_update("title", "x" * 2001)["title"][
                    0
                ]["text"]["content"]
            ),
        )

    def test_update_page_properties_matches_schema_case_insensitively(self):
        """Page updates should use canonical schema names and formatted values."""
        page_id = "123e4567-e89b-12d3-a456-426614174000"
        self.client.notion_client.databases.retrieve.return_value = {
            "properties": {"Title": {"type": "title"}, "Count": {"type": "number"}}
        }

        updated = self.client.update_page_properties(
            "database-id", page_id, {"title": "Example", "count": "3", "missing": "x"}
        )

        self.assertTrue(updated)
        self.client.notion_client.pages.update.assert_called_once_with(
            page_id=page_id,
            properties={
                "Title": {"title": [{"text": {"content": "Example"}}]},
                "Count": {"number": 3},
            },
        )

    def test_update_page_properties_rejects_invalid_page_or_empty_updates(self):
        """Invalid page IDs and values not in the schema should not call the API."""
        self.assertFalse(
            self.client.update_page_properties("database-id", "invalid", {"Title": "x"})
        )
        self.client.notion_client.databases.retrieve.return_value = {
            "properties": {"Title": {"type": "title"}}
        }
        self.assertFalse(
            self.client.update_page_properties(
                "database-id",
                "123e4567-e89b-12d3-a456-426614174000",
                {"Missing": "x"},
            )
        )
        self.client.notion_client.pages.update.assert_not_called()

    def test_create_page_formats_schema_properties(self):
        """Page creation should format values against the retrieved database schema."""
        self.client.notion_client.databases.retrieve.return_value = {
            "properties": {"Title": {"type": "title"}}
        }
        self.client.notion_client.pages.create.return_value = {"id": "page-1"}

        page_id = self.client.create_page("database-id", {"title": "Example"})

        self.assertEqual("page-1", page_id)
        self.client.notion_client.pages.create.assert_called_once_with(
            parent={"database_id": "database-id"},
            properties={"Title": {"title": [{"text": {"content": "Example"}}]}},
        )


if __name__ == "__main__":
    unittest.main()
