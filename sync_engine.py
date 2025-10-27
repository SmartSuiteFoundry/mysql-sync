"""
Sync Engine
-----------
Core synchronization logic with idempotency support.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from mysql_client import MySQLClient
from smartsuite_client import SmartSuiteClient
from state_manager import StateManager
from config_loader import SyncConfig

logger = logging.getLogger(__name__)


class SyncEngine:
    """Handles synchronization between MySQL and SmartSuite."""

    def __init__(
        self,
        mysql_client: MySQLClient,
        smartsuite_client: SmartSuiteClient,
        state_manager: StateManager
    ):
        """
        Initialize sync engine.

        Args:
            mysql_client: MySQL database client
            smartsuite_client: SmartSuite API client
            state_manager: State management instance
        """
        self.mysql = mysql_client
        self.smartsuite = smartsuite_client
        self.state = state_manager

    def sync(self, config: SyncConfig) -> Dict[str, Any]:
        """
        Execute a sync operation.

        Args:
            config: Sync configuration

        Returns:
            Dictionary with sync results (records processed, created, updated, etc.)
        """
        logger.info(f"=" * 70)
        logger.info(f"Starting sync: {config.name}")
        logger.info(f"Description: {config.description}")
        logger.info(f"=" * 70)

        # Start tracking this sync run
        run_id = self.state.start_sync_run(config.name)

        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }

        try:
            # Get last sync time for incremental sync
            last_sync_time = self.state.get_last_sync_time(config.name)
            logger.info(f"Last sync time: {last_sync_time or 'Never'}")

            # Execute source query
            query_params = {'last_sync_time': last_sync_time}
            source_records = self.mysql.execute_query(config.query, query_params)

            logger.info(f"Retrieved {len(source_records)} records from MySQL")

            if not source_records:
                logger.info("No records to sync")
                self.state.complete_sync_run(
                    run_id,
                    status='success',
                    records_processed=0
                )
                return stats

            # Process each record
            for record in source_records:
                try:
                    result = self._sync_record(config, record)
                    stats['processed'] += 1

                    if result == 'created':
                        stats['created'] += 1
                    elif result == 'updated':
                        stats['updated'] += 1
                    elif result == 'skipped':
                        stats['skipped'] += 1

                except Exception as e:
                    logger.error(f"Failed to sync record: {e}")
                    logger.error(f"Record data: {record}")
                    stats['errors'] += 1

            # Update last sync time
            current_time = datetime.utcnow().isoformat()
            self.state.update_last_sync_time(config.name, current_time)

            # Mark sync run as complete
            self.state.complete_sync_run(
                run_id,
                status='success',
                records_processed=stats['processed'],
                records_created=stats['created'],
                records_updated=stats['updated'],
                records_skipped=stats['skipped']
            )

            logger.info(f"Sync complete: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)

            self.state.complete_sync_run(
                run_id,
                status='failed',
                error_message=str(e)
            )

            raise

    def _sync_record(self, config: SyncConfig, source_record: Dict[str, Any]) -> str:
        """
        Sync a single record with idempotency.

        Args:
            config: Sync configuration
            source_record: Source database record

        Returns:
            Action taken: 'created', 'updated', or 'skipped'
        """
        # Get source primary key
        source_id = str(source_record[config.primary_key])

        # Map record to SmartSuite format
        mapped_record = config.map_record(source_record)

        # Calculate hash for change detection
        data_hash = self.state.calculate_hash(mapped_record)

        # Check if record already exists
        existing_mapping = self.state.get_record_mapping(config.name, source_id)

        if existing_mapping:
            # Record exists - check if data has changed
            if existing_mapping['data_hash'] == data_hash:
                logger.debug(f"Record {source_id} unchanged, skipping")
                return 'skipped'

            # Data has changed - update record
            logger.info(f"Updating record {source_id} in SmartSuite")

            try:
                self.smartsuite.update_record(
                    table_id=config.table_id,
                    record_id=existing_mapping['smartsuite_record_id'],
                    updates=mapped_record
                )

                # Update mapping with new hash
                self.state.save_record_mapping(
                    sync_name=config.name,
                    source_id=source_id,
                    smartsuite_record_id=existing_mapping['smartsuite_record_id'],
                    data_hash=data_hash
                )

                return 'updated'

            except Exception as e:
                logger.error(f"Failed to update record {source_id}: {e}")
                raise

        else:
            # Record doesn't exist - create new record
            logger.info(f"Creating new record {source_id} in SmartSuite")

            try:
                created_record = self.smartsuite.create_record(
                    table_id=config.table_id,
                    record_data=mapped_record
                )

                smartsuite_id = created_record['id']

                # Save mapping
                self.state.save_record_mapping(
                    sync_name=config.name,
                    source_id=source_id,
                    smartsuite_record_id=smartsuite_id,
                    data_hash=data_hash
                )

                return 'created'

            except Exception as e:
                logger.error(f"Failed to create record {source_id}: {e}")
                raise

    def get_sync_status(self, sync_name: str) -> Dict[str, Any]:
        """
        Get status and statistics for a sync.

        Args:
            sync_name: Name of the sync configuration

        Returns:
            Dictionary with sync status and recent history
        """
        stats = self.state.get_sync_statistics(sync_name, limit=5)
        last_sync_time = self.state.get_last_sync_time(sync_name)

        return {
            'sync_name': sync_name,
            'last_sync_time': last_sync_time,
            'recent_runs': stats
        }
