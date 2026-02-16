# Copyright (c) 2026
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Notion database client for video management.

Provides a client interface to the Notion API for reading and writing video
data including transcripts, summaries, and metadata. Handles property type
conversion between string representations and Notion API formats.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict

from notion_client import Client as NotionClient

logger = logging.getLogger(__name__)


class Client:
    """Client for interacting with Notion databases.

    Handles all database operations including querying properties, retrieving
    page data, and updating records. Manages conversion between string values
    and Notion-specific property types.
    """

    def __init__(self, token: str):
        """Initialize Notion client with authentication token.

        Args:
            token: Notion API authentication token for accessing databases.
        """
        logger.debug("Initializing Notion client")
        self.client = NotionClient(auth=token)

    def _user_to_string(self, user: Dict[str, Any]) -> str:
        """Convert a Notion user object to a readable string.

        Args:
            user: Dictionary containing Notion user data with 'id' and 'name' keys.

        Returns:
            Formatted string with user ID and name.
        """
        user_id = user.get("id", "")
        name = user.get("name") or "Unknown Name"
        return f"{user_id}: {name}"

    def _extract_value_to_string(self, property: Dict[str, Any]) -> str:
        """Extract and convert a property value to string representation.

        Routes extraction to appropriate handler based on property object type,
        supporting both single property items and lists of property items.

        Args:
            property: The Notion property object to extract.

        Returns:
            String representation of the property value.
        """
        if property.get("object") == "property_item":
            return self._extract_property_item_value_to_string(property)
        elif property.get("object") == "list":
            results = property.get("results", [])
            return ", ".join(
                self._extract_property_item_value_to_string(result)
                for result in results
            )
        return ""

    def _extract_property_item_value_to_string(self, property: Dict[str, Any]) -> str:
        """Convert individual Notion property items to string based on type.

        Handles all Notion property types including text, dates, numbers, users,
        selects, formulas, rollups, and more, converting them to readable strings.
        Returns placeholder "???" for unsupported or incomplete property types.

        Args:
            property: A Notion property item with 'type' key and type-specific data.

        Returns:
            String representation of the property value.
        """
        prop_type = property.get("type")

        if prop_type == "checkbox":
            # Boolean property - convert to string representation
            return str(property.get("checkbox", ""))
        elif prop_type == "created_by":
            # User who created the item
            return self._user_to_string(property.get("created_by", {}))
        elif prop_type == "created_time":
            # Timestamp of creation - convert to ISO format
            ct = property.get("created_time")
            return (
                datetime.fromisoformat(ct.replace("Z", "+00:00")).isoformat()
                if ct
                else ""
            )
        elif prop_type == "date":
            # Date property - extract start date and convert to ISO format
            date_obj = property.get("date")
            return (
                datetime.fromisoformat(
                    date_obj["start"].replace("Z", "+00:00")
                ).isoformat()
                if date_obj
                else ""
            )
        elif prop_type == "email":
            # Email property - return email string
            return property.get("email") or ""
        elif prop_type == "url":
            # URL property - return URL string
            return property.get("url") or ""
        elif prop_type == "number":
            # Numeric property - convert to string
            num = property.get("number")
            return str(num) if isinstance(num, (int, float)) else ""
        elif prop_type == "phone_number":
            # Phone number property - return string
            return property.get("phone_number") or ""
        elif prop_type == "select":
            # Single select property - return ID and name
            select = property.get("select")
            if not select:
                return ""
            return f"{select.get('id', '')} {select.get('name', '')}"
        elif prop_type == "multi_select":
            # Multiple select property - return comma-separated ID and name pairs
            multi_select = property.get("multi_select", [])
            if not multi_select:
                return ""
            return ", ".join(
                f"{opt.get('id', '')} {opt.get('name', '')}" for opt in multi_select
            )
        elif prop_type == "people":
            # Person property - convert user info to string
            return self._user_to_string(property.get("people", {}))
        elif prop_type == "last_edited_by":
            # User who last edited - convert user info to string
            return self._user_to_string(property.get("last_edited_by", {}))
        elif prop_type == "last_edited_time":
            # Timestamp of last edit - convert to ISO format
            let = property.get("last_edited_time")
            return (
                datetime.fromisoformat(let.replace("Z", "+00:00")).isoformat()
                if let
                else ""
            )
        elif prop_type == "title":
            # Title property - extract plain text content
            return property.get("title", {}).get("plain_text", "")
        elif prop_type == "rich_text":
            # Rich text property - extract plain text content
            return property.get("rich_text", {}).get("plain_text", "")
        elif prop_type == "files":
            # Files property - return comma-separated file names
            files = property.get("files", [])
            return ", ".join(file.get("name", "") for file in files)
        elif prop_type == "formula":
            # Formula result - handle different formula result types
            formula = property.get("formula", {})
            formula_type = formula.get("type")
            if formula_type == "string":
                return formula.get("string") or "???"
            elif formula_type == "number":
                num = formula.get("number")
                return str(num) if num is not None else "???"
            elif formula_type == "boolean":
                bool_val = formula.get("boolean")
                return str(bool_val) if bool_val is not None else "???"
            elif formula_type == "date":
                date_obj = formula.get("date")
                return (
                    datetime.fromisoformat(
                        date_obj["start"].replace("Z", "+00:00")
                    ).isoformat()
                    if date_obj and date_obj.get("start")
                    else "???"
                )
            return "???"
        elif prop_type == "rollup":
            # Rollup property - handle different aggregation result types
            rollup = property.get("rollup", {})
            rollup_type = rollup.get("type")
            if rollup_type == "number":
                num = rollup.get("number")
                return str(num) if num is not None else "???"
            elif rollup_type == "date":
                date_obj = rollup.get("date")
                return (
                    datetime.fromisoformat(
                        date_obj["start"].replace("Z", "+00:00")
                    ).isoformat()
                    if date_obj and date_obj.get("start")
                    else "???"
                )
            elif rollup_type == "array":
                # Array results are serialized as JSON
                return json.dumps(rollup.get("array", []))
            elif rollup_type in ("incomplete", "unsupported"):
                return rollup_type
            return "???"
        elif prop_type == "relation":
            # Relation property - return related page ID
            relation = property.get("relation")
            if relation:
                return relation.get("id", "???")
            return "???"
        elif prop_type == "status":
            # Status property - return status name
            return property.get("status", {}).get("name", "")
        elif prop_type == "button":
            # Button property - return button name
            return property.get("button", {}).get("name", "")
        elif prop_type == "unique_id":
            # Unique ID property - combine prefix and number
            unique_id = property.get("unique_id", {})
            prefix = unique_id.get("prefix") or ""
            number = unique_id.get("number") or ""
            return f"{prefix}{number}"
        elif prop_type == "verification":
            # Verification property - return verification state
            return property.get("verification", {}).get("state", "")

        # Unknown property type
        return ""

    def get_database_content(self, database_id: str):
        """Retrieve all page records from a Notion database.

        Queries the database to get all page IDs and metadata that will be
        processed. Uses Notion's data source query API.

        Args:
            database_id: The Notion database ID to query.

        Returns:
            List of page objects containing database records.
        """
        search_results = self.client.search(
            filter={"property": "object", "value": "data_source"}
        )
        query_response = self.client.data_sources.query(
            data_source_id=search_results["results"][0]["id"]
        )
        return query_response.get("results", [])

    def get_page_properties(self, page_id: str):
        """Retrieve all properties from a Notion page.

        Fetches all property values from a page and converts them to string
        representations for easier processing.

        Args:
            page_id: The ID of the Notion page to retrieve.

        Returns:
            Dictionary mapping property names to their string values.
        """
        page = self.client.pages.retrieve(page_id=page_id)
        properties = {}
        for name, property in page["properties"].items():
            property_response = self.client.pages.properties.retrieve(
                page_id=page_id, property_id=property["id"]
            )
            properties[name] = self._extract_value_to_string(property_response)
        return properties

    def get_page_properties_from_database(self, database_id: str):
        """Retrieve all page properties from a database.

        Fetches all pages in the database and extracts their properties,
        adding the page ID to each property set for later reference.

        Args:
            database_id: The Notion database ID containing the pages.

        Returns:
            List of dictionaries, each containing a page's properties plus its ID.
        """
        pages = self.get_database_content(database_id)
        all_properties = []
        for page in pages:
            properties = self.get_page_properties(page["id"])
            properties["ID"] = page["id"]
            all_properties.append(properties)
        return all_properties

    def _format_property_for_update(self, prop_type: str, value: str) -> Dict[str, Any]:
        """Convert string value to Notion API format based on property type.

        Transforms a string value into the appropriate Notion API structure
        for the given property type. Handles type conversion and validation.

        Args:
            prop_type: The Notion property type (e.g., 'title', 'number', 'checkbox').
            value: The string value to format.

        Returns:
            Dictionary in Notion API format for the property, or None if formatting fails.

        Raises:
            Prints warning on ValueError or TypeError but returns None instead of raising.
        """
        if not value:
            return None

        value = str(value).strip()
        if not value:
            return None

        try:
            if prop_type in ("title", "rich_text"):
                # Text properties use nested text content structure
                return {prop_type: [{"text": {"content": value}}]}
            elif prop_type == "checkbox":
                # Convert string to boolean
                return {"checkbox": value.lower() in ("true", "1", "yes", "on")}
            elif prop_type == "number":
                # Parse as float or int depending on format
                return {"number": float(value) if "." in value else int(value)}
            elif prop_type == "select":
                # Single select by name
                return {"select": {"name": value}}
            elif prop_type == "multi_select":
                # Multiple selections parsed from comma-separated list
                options = [opt.strip() for opt in value.split(",")]
                return {"multi_select": [{"name": opt} for opt in options if opt]}
            elif prop_type == "date":
                # Date in ISO format
                return {"date": {"start": value}}
            elif prop_type == "url":
                # URL string
                return {"url": value}
            elif prop_type == "email":
                # Email string
                return {"email": value}
            elif prop_type == "phone_number":
                # Phone number string
                return {"phone_number": value}
            elif prop_type == "status":
                # Status by name
                return {"status": {"name": value}}
            else:
                # Unsupported property type
                return None
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to format {prop_type} with value '{value}': {e}")
            return None

    def get_database_schema(self, database_id: str) -> Dict[str, str]:
        """Retrieve all property names and types from a database.

        Fetches the database schema to understand available properties and
        their types for validation and formatting during updates.

        Args:
            database_id: The Notion database ID to examine.

        Returns:
            Dictionary mapping property names to their Notion type identifiers.
        """
        database = self.client.databases.retrieve(database_id=database_id)
        db_properties = database.get("properties", {})
        schema = {}
        for prop_name, prop_config in db_properties.items():
            schema[prop_name] = prop_config.get("type", "unknown")
        return schema

    def update_page_properties(
        self, database_id: str, page_id: str, properties: Dict[str, str]
    ) -> bool:
        """Update page properties in a Notion database.

        Takes string values from a dictionary and updates the corresponding
        page properties in Notion, handling type conversion and validation.
        Uses case-insensitive property name matching for robustness.

        Args:
            database_id: The ID of the database containing the page.
            page_id: The ID of the page to update.
            properties: Dictionary mapping property names (strings) to values (strings).

        Returns:
            True if the update was successful, False if an error occurred.

        Note:
            Prints debug information and warnings for troubleshooting.
        """
        # Get database schema to determine property types
        try:
            database = self.client.databases.retrieve(database_id=database_id)
            db_properties = database.get("properties", {})

            # Debug: log database response
            logger.debug(
                f"Database response keys: {database.keys() if isinstance(database, dict) else 'not a dict'}"
            )
            logger.debug(
                f"Available properties in database: {list(db_properties.keys())}"
            )

            # If no properties found, try querying the page instead
            if not db_properties:
                logger.warning(
                    "Database has no properties. Trying to retrieve from page instead."
                )
                page = self.client.pages.retrieve(page_id=page_id)
                db_properties = page.get("properties", {})
                logger.debug(f"Properties from page: {list(db_properties.keys())}")
        except Exception as e:
            logger.error(f"Error retrieving database schema: {e}")
            return False

        # Format properties according to their types
        # Create a case-insensitive mapping of property names for matching
        prop_name_map = {name.lower(): name for name in db_properties.keys()}

        formatted_properties = {}
        for prop_name, prop_value in properties.items():
            # Try to find property with case-insensitive matching
            actual_prop_name = prop_name_map.get(prop_name.lower())
            if not actual_prop_name:
                logger.warning(f"Property '{prop_name}' not found in database schema")
                logger.debug(f"Available properties: {list(db_properties.keys())}")
                continue

            # Get the property type and format the value
            prop_type = db_properties[actual_prop_name].get("type")
            formatted = self._format_property_for_update(prop_type, prop_value)
            if formatted:
                formatted_properties[actual_prop_name] = formatted

        # Validate that we have properties to update
        if not formatted_properties:
            logger.warning("No valid properties to update")
            return False

        # Update the page via the Notion API
        try:
            self.client.pages.update(
                page_id=page_id,
                properties=formatted_properties,
            )
            return True
        except Exception as e:
            logger.error(f"Error updating page: {e}")
            return False
