"""
State Manager
-------------
Handles SQLite-based state tracking for sync operations.
Maintains record mappings and sync history for idempotency.
"""

import sqlite3
import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
from pathlib import Path


class StateManager:
    """Manages sync state using SQLite database."""

    def __init__(self, db_path: str = "sync_state.db"):
        """
        Initialize state manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Table to track sync runs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_name TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT NOT NULL,
                    records_processed INTEGER DEFAULT 0,
                    records_created INTEGER DEFAULT 0,
                    records_updated INTEGER DEFAULT 0,
                    records_skipped INTEGER DEFAULT 0,
                    error_message TEXT,
                    UNIQUE(sync_name, started_at)
                )
            """)

            # Table to track individual record mappings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS record_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_name TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    smartsuite_record_id TEXT NOT NULL,
                    data_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(sync_name, source_id)
                )
            """)

            # Index for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_record_mappings_lookup
                ON record_mappings(sync_name, source_id)
            """)

            # Table to track last successful sync timestamp per sync
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_metadata (
                    sync_name TEXT PRIMARY KEY,
                    last_sync_time TEXT,
                    last_successful_run TEXT
                )
            """)

            conn.commit()

    def get_last_sync_time(self, sync_name: str) -> Optional[str]:
        """
        Get the last successful sync timestamp for incremental queries.

        Args:
            sync_name: Name of the sync configuration

        Returns:
            ISO timestamp of last sync, or None if never synced
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT last_sync_time FROM sync_metadata WHERE sync_name = ?",
                (sync_name,)
            )
            result = cursor.fetchone()
            return result[0] if result else None

    def update_last_sync_time(self, sync_name: str, sync_time: str):
        """
        Update the last sync timestamp.

        Args:
            sync_name: Name of the sync configuration
            sync_time: ISO timestamp of sync
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_metadata (sync_name, last_sync_time, last_successful_run)
                VALUES (?, ?, ?)
                ON CONFLICT(sync_name) DO UPDATE SET
                    last_sync_time = excluded.last_sync_time,
                    last_successful_run = excluded.last_successful_run
            """, (sync_name, sync_time, datetime.utcnow().isoformat()))
            conn.commit()

    def start_sync_run(self, sync_name: str) -> int:
        """
        Record the start of a sync run.

        Args:
            sync_name: Name of the sync configuration

        Returns:
            Sync run ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_runs (sync_name, started_at, status)
                VALUES (?, ?, 'running')
            """, (sync_name, datetime.utcnow().isoformat()))
            conn.commit()
            return cursor.lastrowid

    def complete_sync_run(
        self,
        run_id: int,
        status: str,
        records_processed: int = 0,
        records_created: int = 0,
        records_updated: int = 0,
        records_skipped: int = 0,
        error_message: Optional[str] = None
    ):
        """
        Mark a sync run as complete.

        Args:
            run_id: Sync run ID
            status: Final status ('success' or 'failed')
            records_processed: Total records processed
            records_created: Records created in SmartSuite
            records_updated: Records updated in SmartSuite
            records_skipped: Records skipped (no changes)
            error_message: Error message if failed
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sync_runs
                SET completed_at = ?,
                    status = ?,
                    records_processed = ?,
                    records_created = ?,
                    records_updated = ?,
                    records_skipped = ?,
                    error_message = ?
                WHERE id = ?
            """, (
                datetime.utcnow().isoformat(),
                status,
                records_processed,
                records_created,
                records_updated,
                records_skipped,
                error_message,
                run_id
            ))
            conn.commit()

    def calculate_hash(self, data: Dict[str, Any]) -> str:
        """
        Calculate hash of record data for change detection.

        Args:
            data: Record data dictionary

        Returns:
            SHA256 hash of normalized data
        """
        # Sort keys for consistent hashing
        normalized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get_record_mapping(
        self,
        sync_name: str,
        source_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get existing record mapping.

        Args:
            sync_name: Name of the sync configuration
            source_id: Source system primary key

        Returns:
            Mapping dict with smartsuite_record_id and data_hash, or None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT smartsuite_record_id, data_hash, created_at, updated_at
                FROM record_mappings
                WHERE sync_name = ? AND source_id = ?
            """, (sync_name, source_id))

            result = cursor.fetchone()
            if result:
                return {
                    "smartsuite_record_id": result[0],
                    "data_hash": result[1],
                    "created_at": result[2],
                    "updated_at": result[3]
                }
            return None

    def save_record_mapping(
        self,
        sync_name: str,
        source_id: str,
        smartsuite_record_id: str,
        data_hash: str
    ):
        """
        Save or update record mapping.

        Args:
            sync_name: Name of the sync configuration
            source_id: Source system primary key
            smartsuite_record_id: SmartSuite record ID
            data_hash: Hash of record data
        """
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO record_mappings
                (sync_name, source_id, smartsuite_record_id, data_hash, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(sync_name, source_id) DO UPDATE SET
                    smartsuite_record_id = excluded.smartsuite_record_id,
                    data_hash = excluded.data_hash,
                    updated_at = excluded.updated_at
            """, (sync_name, source_id, smartsuite_record_id, data_hash, now, now))
            conn.commit()

    def get_sync_statistics(self, sync_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent sync run statistics.

        Args:
            sync_name: Name of the sync configuration
            limit: Number of recent runs to return

        Returns:
            List of sync run dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT *
                FROM sync_runs
                WHERE sync_name = ?
                ORDER BY started_at DESC
                LIMIT ?
            """, (sync_name, limit))

            return [dict(row) for row in cursor.fetchall()]
