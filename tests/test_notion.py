"""Tests for the Notion client module."""

from unittest.mock import patch

from yt_summarizer.notion import Client


class TestNotionClient:
    """Test cases for Notion Client class."""

    @patch("yt_summarizer.notion.NotionClient")
    def test_init(self, mock_notion_client):
        """Test Notion client initialization."""
        token = "test-token-12345"

        client = Client(token=token)

        mock_notion_client.assert_called_once_with(auth=token)
        assert client.client is not None

    @patch("yt_summarizer.notion.NotionClient")
    def test_user_to_string(self, mock_notion_client):
        """Test conversion of Notion user object to string."""
        client = Client(token="test-token")

        user = {"id": "user-123", "name": "John Doe"}
        result = client._user_to_string(user)

        assert result == "user-123: John Doe"

    @patch("yt_summarizer.notion.NotionClient")
    def test_user_to_string_missing_name(self, mock_notion_client):
        """Test conversion of user with missing name."""
        client = Client(token="test-token")

        user = {"id": "user-123", "name": None}
        result = client._user_to_string(user)

        assert result == "user-123: Unknown Name"

    @patch("yt_summarizer.notion.NotionClient")
    def test_user_to_string_missing_id(self, mock_notion_client):
        """Test conversion of user with missing id."""
        client = Client(token="test-token")

        user = {"name": "John Doe"}
        result = client._user_to_string(user)

        assert result == ": John Doe"

    @patch("yt_summarizer.notion.NotionClient")
    def test_extract_property_item_value_checkbox_true(self, mock_notion_client):
        """Test extracting checkbox property value (true)."""
        client = Client(token="test-token")

        property_item = {"type": "checkbox", "checkbox": True}
        result = client._extract_property_item_value_to_string(property_item)

        assert result == "True"

    @patch("yt_summarizer.notion.NotionClient")
    def test_extract_property_item_value_checkbox_false(self, mock_notion_client):
        """Test extracting checkbox property value (false)."""
        client = Client(token="test-token")

        property_item = {"type": "checkbox", "checkbox": False}
        result = client._extract_property_item_value_to_string(property_item)

        assert result == "False"

    @patch("yt_summarizer.notion.NotionClient")
    def test_extract_property_item_value_title(self, mock_notion_client):
        """Test extracting title property value."""
        client = Client(token="test-token")

        property_item = {"type": "title", "title": {"plain_text": "Sample Title"}}
        result = client._extract_property_item_value_to_string(property_item)

        assert result == "Sample Title"

    @patch("yt_summarizer.notion.NotionClient")
    def test_extract_property_item_value_rich_text(self, mock_notion_client):
        """Test extracting rich_text property value."""
        client = Client(token="test-token")

        property_item = {
            "type": "rich_text",
            "rich_text": {"plain_text": "Sample rich text"},
        }
        result = client._extract_property_item_value_to_string(property_item)

        assert result == "Sample rich text"

    @patch("yt_summarizer.notion.NotionClient")
    def test_extract_property_item_value_number(self, mock_notion_client):
        """Test extracting number property value."""
        client = Client(token="test-token")

        property_item = {"type": "number", "number": 42}
        result = client._extract_property_item_value_to_string(property_item)

        assert result == "42"

    @patch("yt_summarizer.notion.NotionClient")
    def test_extract_property_item_value_select(self, mock_notion_client):
        """Test extracting select property value."""
        client = Client(token="test-token")

        property_item = {
            "type": "select",
            "select": {"id": "id-123", "name": "Option 1"},
        }
        result = client._extract_property_item_value_to_string(property_item)

        # Implementation returns "id name" format
        assert result == "id-123 Option 1"

    @patch("yt_summarizer.notion.NotionClient")
    def test_extract_property_item_value_url(self, mock_notion_client):
        """Test extracting URL property value."""
        client = Client(token="test-token")

        property_item = {"type": "url", "url": "https://example.com"}
        result = client._extract_property_item_value_to_string(property_item)

        assert result == "https://example.com"

    @patch("yt_summarizer.notion.NotionClient")
    def test_extract_property_item_value_email(self, mock_notion_client):
        """Test extracting email property value."""
        client = Client(token="test-token")

        property_item = {"type": "email", "email": "test@example.com"}
        result = client._extract_property_item_value_to_string(property_item)

        assert result == "test@example.com"

    @patch("yt_summarizer.notion.NotionClient")
    def test_extract_value_to_string_property_item(self, mock_notion_client):
        """Test extract_value_to_string with property_item object."""
        client = Client(token="test-token")

        property_obj = {
            "object": "property_item",
            "type": "rich_text",
            "rich_text": {"plain_text": "Test content"},
        }
        result = client._extract_value_to_string(property_obj)

        assert result == "Test content"

    @patch("yt_summarizer.notion.NotionClient")
    def test_extract_value_to_string_list(self, mock_notion_client):
        """Test extract_value_to_string with list object."""
        client = Client(token="test-token")

        property_obj = {
            "object": "list",
            "results": [
                {"type": "rich_text", "rich_text": {"plain_text": "Item 1"}},
                {"type": "rich_text", "rich_text": {"plain_text": "Item 2"}},
            ],
        }
        result = client._extract_value_to_string(property_obj)

        assert "Item 1" in result
        assert "Item 2" in result
        assert ", " in result

    @patch("yt_summarizer.notion.NotionClient")
    def test_format_property_for_update_title(self, mock_notion_client):
        """Test formatting title property for update."""
        client = Client(token="test-token")

        result = client._format_property_for_update("title", "New Title")

        assert result == {"title": [{"text": {"content": "New Title"}}]}

    @patch("yt_summarizer.notion.NotionClient")
    def test_format_property_for_update_checkbox_true(self, mock_notion_client):
        """Test formatting checkbox property for update (true)."""
        client = Client(token="test-token")

        result = client._format_property_for_update("checkbox", "true")

        assert result == {"checkbox": True}

    @patch("yt_summarizer.notion.NotionClient")
    def test_format_property_for_update_checkbox_false(self, mock_notion_client):
        """Test formatting checkbox property for update (false)."""
        client = Client(token="test-token")

        result = client._format_property_for_update("checkbox", "false")

        assert result == {"checkbox": False}

    @patch("yt_summarizer.notion.NotionClient")
    def test_format_property_for_update_number_integer(self, mock_notion_client):
        """Test formatting integer number property for update."""
        client = Client(token="test-token")

        result = client._format_property_for_update("number", "42")

        assert result == {"number": 42}

    @patch("yt_summarizer.notion.NotionClient")
    def test_format_property_for_update_number_float(self, mock_notion_client):
        """Test formatting float number property for update."""
        client = Client(token="test-token")

        result = client._format_property_for_update("number", "3.14")

        assert result == {"number": 3.14}

    @patch("yt_summarizer.notion.NotionClient")
    def test_format_property_for_update_select(self, mock_notion_client):
        """Test formatting select property for update."""
        client = Client(token="test-token")

        result = client._format_property_for_update("select", "Option 1")

        assert result == {"select": {"name": "Option 1"}}

    @patch("yt_summarizer.notion.NotionClient")
    def test_format_property_for_update_multi_select(self, mock_notion_client):
        """Test formatting multi_select property for update."""
        client = Client(token="test-token")

        result = client._format_property_for_update(
            "multi_select", "Option1, Option2, Option3"
        )

        assert result == {
            "multi_select": [
                {"name": "Option1"},
                {"name": "Option2"},
                {"name": "Option3"},
            ]
        }

    @patch("yt_summarizer.notion.NotionClient")
    def test_format_property_for_update_url(self, mock_notion_client):
        """Test formatting URL property for update."""
        client = Client(token="test-token")

        result = client._format_property_for_update("url", "https://example.com")

        assert result == {"url": "https://example.com"}

    @patch("yt_summarizer.notion.NotionClient")
    def test_format_property_for_update_email(self, mock_notion_client):
        """Test formatting email property for update."""
        client = Client(token="test-token")

        result = client._format_property_for_update("email", "test@example.com")

        assert result == {"email": "test@example.com"}

    @patch("yt_summarizer.notion.NotionClient")
    def test_format_property_for_update_empty_value(self, mock_notion_client):
        """Test formatting with empty value returns None."""
        client = Client(token="test-token")

        result = client._format_property_for_update("title", "")

        assert result is None

    @patch("yt_summarizer.notion.NotionClient")
    def test_format_property_for_update_whitespace_value(self, mock_notion_client):
        """Test formatting with whitespace-only value returns None."""
        client = Client(token="test-token")

        result = client._format_property_for_update("title", "   ")

        assert result is None

    @patch("yt_summarizer.notion.NotionClient")
    def test_format_property_for_update_unsupported_type(self, mock_notion_client):
        """Test formatting unsupported property type returns None."""
        client = Client(token="test-token")

        result = client._format_property_for_update("unsupported_type", "value")

        assert result is None

    @patch("yt_summarizer.notion.NotionClient")
    def test_get_database_schema(self, mock_notion_client):
        """Test retrieving database schema."""
        mock_database = {
            "properties": {
                "Title": {"type": "title"},
                "URL": {"type": "url"},
                "Summary": {"type": "rich_text"},
                "Count": {"type": "number"},
            }
        }

        mock_notion_client.return_value.databases.retrieve.return_value = mock_database

        client = Client(token="test-token")
        schema = client.get_database_schema("db-123")

        assert schema == {
            "Title": "title",
            "URL": "url",
            "Summary": "rich_text",
            "Count": "number",
        }

    @patch("yt_summarizer.notion.NotionClient")
    def test_get_page_properties_from_database(self, mock_notion_client):
        """Test retrieving page properties from database."""
        mock_pages = [
            {"id": "page-1"},
            {"id": "page-2"},
        ]

        mock_notion_client.return_value.search.return_value = {
            "results": [{"id": "ds-1"}]
        }
        mock_notion_client.return_value.data_sources.query.return_value = {
            "results": mock_pages
        }
        mock_notion_client.return_value.pages.retrieve.return_value = {
            "properties": {
                "Title": {"id": "title-id", "type": "title"},
                "URL": {"id": "url-id", "type": "url"},
            }
        }
        mock_notion_client.return_value.pages.properties.retrieve.side_effect = [
            {
                "object": "property_item",
                "type": "text",
                "text": {"content": "Test Title"},
            },
            {"object": "property_item", "type": "url", "url": "https://example.com"},
            {
                "object": "property_item",
                "type": "text",
                "text": {"content": "Test Title 2"},
            },
            {"object": "property_item", "type": "url", "url": "https://example2.com"},
        ]

        client = Client(token="test-token")
        properties = client.get_page_properties_from_database("db-123")

        assert len(properties) == 2
        assert all("ID" in p for p in properties)
        assert properties[0]["ID"] == "page-1"
        assert properties[1]["ID"] == "page-2"

    @patch("yt_summarizer.notion.NotionClient")
    def test_update_page_properties_success(self, mock_notion_client):
        """Test successful page properties update."""
        mock_database = {
            "properties": {
                "Title": {"type": "title"},
                "Summary": {"type": "rich_text"},
            }
        }

        mock_notion_client.return_value.databases.retrieve.return_value = mock_database
        mock_notion_client.return_value.pages.update.return_value = {}

        client = Client(token="test-token")
        result = client.update_page_properties(
            "db-123", "page-456", {"Title": "New Title", "Summary": "New Summary"}
        )

        assert result is True
        mock_notion_client.return_value.pages.update.assert_called_once()

    @patch("yt_summarizer.notion.NotionClient")
    def test_update_page_properties_no_matching_properties(self, mock_notion_client):
        """Test update when no properties match the database schema."""
        mock_database = {
            "properties": {
                "Title": {"type": "title"},
            }
        }

        mock_notion_client.return_value.databases.retrieve.return_value = mock_database

        client = Client(token="test-token")
        result = client.update_page_properties(
            "db-123", "page-456", {"NonExistent": "Value"}
        )

        assert result is False

    @patch("yt_summarizer.notion.NotionClient")
    def test_update_page_properties_case_insensitive_match(self, mock_notion_client):
        """Test that property name matching is case-insensitive."""
        mock_database = {
            "properties": {
                "Title": {"type": "title"},
            }
        }

        mock_notion_client.return_value.databases.retrieve.return_value = mock_database
        mock_notion_client.return_value.pages.update.return_value = {}

        client = Client(token="test-token")
        result = client.update_page_properties(
            "db-123", "page-456", {"title": "New Title"}  # lowercase
        )

        assert result is True
        mock_notion_client.return_value.pages.update.assert_called_once()

    @patch("yt_summarizer.notion.NotionClient")
    def test_update_page_properties_error_handling(self, mock_notion_client):
        """Test error handling during page update."""
        mock_database = {
            "properties": {
                "Title": {"type": "title"},
            }
        }

        mock_notion_client.return_value.databases.retrieve.return_value = mock_database
        mock_notion_client.return_value.pages.update.side_effect = Exception(
            "API Error"
        )

        client = Client(token="test-token")
        result = client.update_page_properties(
            "db-123", "page-456", {"Title": "New Title"}
        )

        assert result is False
