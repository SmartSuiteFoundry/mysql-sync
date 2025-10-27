#!/usr/bin/env python3
"""
MySQL to SmartSuite Sync
------------------------
Main application entry point.
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

from mysql_client import MySQLClient
from smartsuite_client import SmartSuiteClient
from state_manager import StateManager
from config_loader import ConfigLoader
from sync_engine import SyncEngine
from scheduler import SyncScheduler


def setup_logging(log_level: str = "INFO"):
    """
    Configure logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure logging format
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Set up root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "sync.log")
        ]
    )

    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)


def load_environment():
    """Load environment variables from .env file."""
    load_dotenv()

    # Validate required environment variables
    required_vars = [
        'MYSQL_HOST',
        'MYSQL_USER',
        'MYSQL_PASSWORD',
        'MYSQL_DATABASE',
        'SMARTSUITE_TOKEN',
        'SMARTSUITE_ACCOUNT_ID'
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}"
        )


def initialize_clients():
    """
    Initialize database and API clients.

    Returns:
        Tuple of (mysql_client, smartsuite_client, state_manager)
    """
    # MySQL client
    mysql_client = MySQLClient(
        host=os.getenv('MYSQL_HOST'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DATABASE')
    )

    # SmartSuite client
    smartsuite_client = SmartSuiteClient(
        token=os.getenv('SMARTSUITE_TOKEN'),
        account_id=os.getenv('SMARTSUITE_ACCOUNT_ID')
    )

    # State manager
    state_manager = StateManager(
        db_path=os.getenv('STATE_DB_PATH', 'sync_state.db')
    )

    return mysql_client, smartsuite_client, state_manager


def run_once(args):
    """
    Run sync once and exit.

    Args:
        args: Command line arguments
    """
    logger = logging.getLogger(__name__)

    # Initialize clients
    mysql_client, smartsuite_client, state_manager = initialize_clients()

    # Load configurations
    config_loader = ConfigLoader(args.config)
    syncs = config_loader.get_enabled_syncs()

    if not syncs:
        logger.error("No enabled syncs found in configuration")
        return 1

    # Create sync engine
    sync_engine = SyncEngine(mysql_client, smartsuite_client, state_manager)

    # Run each sync
    overall_success = True
    for sync_config in syncs:
        if args.sync_name and sync_config.name != args.sync_name:
            continue

        try:
            logger.info(f"\nStarting sync: {sync_config.name}")
            stats = sync_engine.sync(sync_config)
            logger.info(f"Completed: {stats}\n")

        except Exception as e:
            logger.error(f"Sync failed: {sync_config.name}", exc_info=True)
            overall_success = False

    return 0 if overall_success else 1


def run_scheduled(args):
    """
    Run syncs on a schedule.

    Args:
        args: Command line arguments
    """
    logger = logging.getLogger(__name__)

    # Initialize clients
    mysql_client, smartsuite_client, state_manager = initialize_clients()

    # Test MySQL connection
    logger.info("Testing MySQL connection...")
    if not mysql_client.test_connection():
        logger.error("Failed to connect to MySQL database")
        return 1
    logger.info("MySQL connection successful")

    # Load configurations
    config_loader = ConfigLoader(args.config)
    syncs = config_loader.get_enabled_syncs()

    if not syncs:
        logger.error("No enabled syncs found in configuration")
        return 1

    # Create sync engine and scheduler
    sync_engine = SyncEngine(mysql_client, smartsuite_client, state_manager)
    scheduler = SyncScheduler(sync_engine)

    # Get interval from environment or args
    interval_minutes = int(os.getenv('SYNC_INTERVAL_MINUTES', args.interval))

    # Schedule each sync
    for sync_config in syncs:
        scheduler.add_sync_job(
            config=sync_config,
            interval_minutes=interval_minutes
        )

    # Run first sync immediately if requested
    if args.run_immediately:
        logger.info("Running initial sync before starting scheduler...")
        for sync_config in syncs:
            try:
                sync_engine.sync(sync_config)
            except Exception as e:
                logger.error(f"Initial sync failed: {sync_config.name}", exc_info=True)

    # Start scheduler (blocking)
    scheduler.start()

    return 0


def validate_config(args):
    """
    Validate configuration file.

    Args:
        args: Command line arguments
    """
    logger = logging.getLogger(__name__)

    try:
        config_loader = ConfigLoader(args.config)
        config_loader.validate_config()
        logger.info("✓ Configuration is valid")
        return 0
    except Exception as e:
        logger.error(f"✗ Configuration validation failed: {e}")
        return 1


def show_status(args):
    """
    Show sync status and history.

    Args:
        args: Command line arguments
    """
    logger = logging.getLogger(__name__)

    # Initialize state manager
    state_manager = StateManager(
        db_path=os.getenv('STATE_DB_PATH', 'sync_state.db')
    )

    # Load configurations
    config_loader = ConfigLoader(args.config)
    syncs = config_loader.load()

    # Show status for each sync
    for sync_config in syncs:
        logger.info(f"\n{'='*70}")
        logger.info(f"Sync: {sync_config.name}")
        logger.info(f"Enabled: {sync_config.enabled}")
        logger.info(f"{'='*70}")

        stats = state_manager.get_sync_statistics(sync_config.name, limit=5)

        if not stats:
            logger.info("No sync history found")
            continue

        logger.info("\nRecent Runs:")
        for run in stats:
            logger.info(f"  • {run['started_at']}: {run['status']}")
            if run['status'] == 'success':
                logger.info(f"    Processed: {run['records_processed']}, "
                          f"Created: {run['records_created']}, "
                          f"Updated: {run['records_updated']}, "
                          f"Skipped: {run['records_skipped']}")
            elif run['error_message']:
                logger.info(f"    Error: {run['error_message']}")

    return 0


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="MySQL to SmartSuite Sync Application"
    )

    parser.add_argument(
        '--config',
        default='config/sync_mappings.yml',
        help='Path to sync configuration file'
    )

    parser.add_argument(
        '--log-level',
        default=os.getenv('LOG_LEVEL', 'INFO'),
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Run once command
    run_once_parser = subparsers.add_parser('run', help='Run sync once and exit')
    run_once_parser.add_argument(
        '--sync-name',
        help='Run only specific sync (by name)'
    )

    # Scheduled command
    schedule_parser = subparsers.add_parser('schedule', help='Run syncs on a schedule')
    schedule_parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='Sync interval in minutes (default: 5)'
    )
    schedule_parser.add_argument(
        '--run-immediately',
        action='store_true',
        help='Run sync immediately before starting scheduler'
    )

    # Validate command
    subparsers.add_parser('validate', help='Validate configuration file')

    # Status command
    subparsers.add_parser('status', help='Show sync status and history')

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    try:
        # Load environment
        load_environment()

        # Execute command
        if args.command == 'run':
            return run_once(args)
        elif args.command == 'schedule':
            return run_scheduled(args)
        elif args.command == 'validate':
            return validate_config(args)
        elif args.command == 'status':
            return show_status(args)
        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
