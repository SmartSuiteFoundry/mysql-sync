"""
SmartSuite API Client
---------------------
Handles all SmartSuite API interactions with error handling.
"""

import time
from typing import Optional
from requests import Session, HTTPError, Response


class SmartSuiteClient:
    """Client for interacting with SmartSuite API."""

    BASE_URL = "https://app.smartsuite.com/api/v1"

    def __init__(self, token: str, account_id: str):
        """
        Initialize SmartSuite client.

        Args:
            token: SmartSuite API token
            account_id: SmartSuite account/workspace ID
        """
        self._session = Session()
        self._session.headers.update({
            "Authorization": f"Token {token}",
            "ACCOUNT-ID": account_id,
            "Content-Type": "application/json",
        })
        self.account_id = account_id

    def _request(self, method: str, endpoint: str, **kwargs) -> Response:
        """
        Make a request to SmartSuite API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response object

        Raises:
            HTTPError: If request fails
        """
        url = f"{self.BASE_URL}{endpoint}"

        try:
            r = self._session.request(method, url, **kwargs)
            r.raise_for_status()
            return r
        except HTTPError as e:
            error_text = e.response.text if hasattr(e.response, 'text') else str(e)
            print(f"❌ SmartSuite {e.response.status_code} on {method} {url}")
            print(f"   Error: {error_text}")
            raise

    def get(self, endpoint: str, **kwargs) -> dict:
        """Make a GET request to SmartSuite API."""
        return self._request("GET", endpoint, **kwargs).json()

    def post(self, endpoint: str, **kwargs) -> dict:
        """Make a POST request to SmartSuite API."""
        return self._request("POST", endpoint, **kwargs).json()

    def put(self, endpoint: str, **kwargs) -> dict:
        """Make a PUT request to SmartSuite API."""
        return self._request("PUT", endpoint, **kwargs).json()

    def patch(self, endpoint: str, **kwargs) -> dict:
        """Make a PATCH request to SmartSuite API."""
        return self._request("PATCH", endpoint, **kwargs).json()

    # ═══════════════════════════════════════════════════════
    #  Application/Table Methods
    # ═══════════════════════════════════════════════════════

    def get_solution_tables(self, solution_id: str) -> list[dict]:
        """
        Get all tables in a solution.

        Args:
            solution_id: SmartSuite solution ID

        Returns:
            List of table/application dictionaries
        """
        return self.get(f"/applications/?solution={solution_id}")

    def get_table_details(self, table_id: str) -> dict:
        """
        Get detailed information about a table.

        Args:
            table_id: SmartSuite table/application ID

        Returns:
            Table details including structure
        """
        return self.get(f"/applications/{table_id}/")

    def duplicate_table(self, table_id: str, new_name: str, duplicate_records: bool = False) -> dict:
        """
        Duplicate a table.

        Args:
            table_id: Source table ID to duplicate
            new_name: Name for the new table
            duplicate_records: Whether to copy existing records

        Returns:
            Response containing new table information
        """
        payload = {
            "name": new_name,
            "duplicate_records": duplicate_records
        }
        print(f"    📋 Duplicating table '{table_id}' as '{new_name}'...")
        return self.post(f"/applications/{table_id}/duplicate/", json=payload)

    def wait_for_table_readiness(self, table_id: str, timeout: int = 120) -> dict:
        """
        Wait for a table to finish duplication process.

        Args:
            table_id: Table ID to check
            timeout: Maximum time to wait in seconds

        Returns:
            Table details once ready

        Raises:
            TimeoutError: If table is not ready within timeout
        """
        print(f"    ⏳ Waiting for table '{table_id}' to be ready...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                table_details = self.get_table_details(table_id)

                if table_details.get("status") != "in_process_of_duplication":
                    print("    ✅ Table is ready.")
                    return table_details

            except HTTPError as e:
                if e.response.status_code != 404:
                    raise

            time.sleep(3)

        raise TimeoutError(f"Table {table_id} was not ready within {timeout} seconds.")

    # ═══════════════════════════════════════════════════════
    #  Field Management Methods
    # ═══════════════════════════════════════════════════════

    def add_field(
        self,
        table_id: str,
        label: str,
        field_type: str,
        params: Optional[dict] = None,
        slug: Optional[str] = None
    ) -> dict:
        """
        Add a new field to a table.

        Args:
            table_id: Table ID to add field to
            label: Display label for the field
            field_type: SmartSuite field type (e.g., 'textfield', 'datefield')
            params: Field parameters (choices, width, etc.)
            slug: Optional custom slug (auto-generated if not provided)

        Returns:
            Response from field creation
        """
        import re
        import random

        if slug is None:
            slug = re.sub(r'\W+', '_', label.lower().strip())
            slug += "_" + ''.join(random.choices('abcdef0123456789', k=4))

        if params is None:
            params = {}

        payload = {
            "field": {
                "slug": slug,
                "label": label,
                "field_type": field_type,
                "params": {"width": 1, **params},
                "is_new": True,
            },
            "field_position": {"prev_sibling_slug": ""},
            "auto_fill_structure_layout": True,
        }

        print(f"    ➕ Adding field '{label}' ({field_type})")
        return self.post(
            f"/applications/{table_id}/add_field/?return_command_id=true",
            json=payload
        )

    # ═══════════════════════════════════════════════════════
    #  Record Methods
    # ═══════════════════════════════════════════════════════

    def create_record(self, table_id: str, record_data: dict) -> dict:
        """
        Create a single record.

        Args:
            table_id: Table ID to create record in
            record_data: Record field values

        Returns:
            Created record
        """
        return self.post(f"/applications/{table_id}/records/", json=record_data)

    def bulk_create_records(self, table_id: str, records: list[dict], batch_size: int = 25) -> list[dict]:
        """
        Create multiple records in batches.

        Args:
            table_id: Table ID to create records in
            records: List of record data dictionaries
            batch_size: Number of records per batch

        Returns:
            List of created records
        """
        if not records:
            print("    ℹ️  No records to add.")
            return []

        all_created = []

        for i in range(0, len(records), batch_size):
            batch = [rec for rec in records[i:i + batch_size] if rec]

            if not batch:
                continue

            print(f"    ➕ Creating {len(batch)} records (batch {i // batch_size + 1})...")

            try:
                response = self.post(
                    f"/applications/{table_id}/records/bulk/",
                    json={"items": batch}
                )

                added_count = len(response) if isinstance(response, list) else 0
                print(f"       ✅ Created {added_count} records.")
                all_created.extend(response if isinstance(response, list) else [])

            except HTTPError as e:
                print(f"       ❌ Batch failed: {e}")
                continue

        return all_created

    def list_records(
        self,
        table_id: str,
        filter_conditions: Optional[dict] = None,
        sort: Optional[list] = None
    ) -> list[dict]:
        """
        List all records in a table with pagination.

        Args:
            table_id: Table ID to query
            filter_conditions: Optional filter conditions
            sort: Optional sort configuration

        Returns:
            List of all records
        """
        records = []
        offset = 0
        limit = 200

        while True:
            payload = {
                "sort": sort or [],
                "filter": filter_conditions or {}
            }

            url = f"/applications/{table_id}/records/list/?offset={offset}&limit={limit}"
            batch = self.post(url, json=payload).get("items", [])

            if not batch:
                break

            records.extend(batch)
            offset += limit

        return records

    def update_record(self, table_id: str, record_id: str, updates: dict) -> dict:
        """
        Update a record.

        Args:
            table_id: Table ID containing the record
            record_id: Record ID to update
            updates: Field updates to apply

        Returns:
            Updated record
        """
        return self.patch(
            f"/applications/{table_id}/records/{record_id}/",
            json=updates
        )

    # ═══════════════════════════════════════════════════════
    #  Comment Methods
    # ═══════════════════════════════════════════════════════

    def create_comment(
        self,
        record_id: str,
        table_id: str,
        text: str,
        assigned_to: Optional[str] = None,
        parent_comment: Optional[str] = None
    ) -> dict:
        """
        Create a comment on a record.

        Args:
            record_id: Record ID to comment on
            table_id: Table ID containing the record
            text: Comment text
            assigned_to: Optional user ID to assign comment to
            parent_comment: Optional parent comment ID for replies

        Returns:
            Created comment
        """
        # Create message document structure
        message_doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": text}
                    ]
                }
            ]
        }

        payload = {
            "assigned_to": assigned_to,
            "message": {"data": message_doc},
            "application": table_id,
            "record": record_id,
        }

        if parent_comment:
            payload["parent_comment"] = parent_comment

        return self.post("/comments/", json=payload)

    # ═══════════════════════════════════════════════════════
    #  Utility Methods
    # ═══════════════════════════════════════════════════════

    def get_field_map(self, table_structure: list[dict]) -> dict:
        """
        Create a field mapping from table structure.

        Args:
            table_structure: List of field definitions from table details

        Returns:
            Dictionary mapping field labels to field information
        """
        field_map = {}

        for field in table_structure:
            field_map[field["label"]] = {
                "slug": field["slug"],
                "field_type": field["field_type"],
                "choices": {
                    str(c["label"]): c["value"]
                    for c in field.get("params", {}).get("choices", [])
                }
            }

        return field_map
