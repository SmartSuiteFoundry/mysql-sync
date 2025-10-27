"""
Scheduler
---------
Manages scheduled sync jobs using APScheduler.
"""

import logging
from typing import List, Optional
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

from sync_engine import SyncEngine
from config_loader import SyncConfig

logger = logging.getLogger(__name__)


class SyncScheduler:
    """Manages scheduled synchronization jobs."""

    def __init__(self, sync_engine: SyncEngine):
        """
        Initialize scheduler.

        Args:
            sync_engine: Sync engine instance
        """
        self.sync_engine = sync_engine
        self.scheduler = BlockingScheduler()
        self._job_ids = {}

    def add_sync_job(
        self,
        config: SyncConfig,
        interval_minutes: int = 5,
        cron_expression: Optional[str] = None
    ):
        """
        Add a scheduled sync job.

        Args:
            config: Sync configuration
            interval_minutes: Run every N minutes (if cron_expression not provided)
            cron_expression: Optional cron expression (e.g., "0 */2 * * *")
        """
        job_id = f"sync_{config.name}"

        # Determine trigger
        if cron_expression:
            trigger = CronTrigger.from_crontab(cron_expression)
            logger.info(f"Scheduling {config.name} with cron: {cron_expression}")
        else:
            trigger = IntervalTrigger(minutes=interval_minutes)
            logger.info(f"Scheduling {config.name} every {interval_minutes} minutes")

        # Add job
        job = self.scheduler.add_job(
            func=self._run_sync,
            trigger=trigger,
            args=[config],
            id=job_id,
            name=config.name,
            replace_existing=True,
            max_instances=1  # Prevent concurrent runs of same sync
        )

        self._job_ids[config.name] = job_id
        logger.info(f"Added job: {job_id}")

    def _run_sync(self, config: SyncConfig):
        """
        Execute a sync job.

        Args:
            config: Sync configuration
        """
        try:
            logger.info(f"\n{'='*70}")
            logger.info(f"Scheduled sync triggered: {config.name}")
            logger.info(f"Time: {datetime.now().isoformat()}")
            logger.info(f"{'='*70}\n")

            stats = self.sync_engine.sync(config)

            logger.info(f"\n{'='*70}")
            logger.info(f"Sync completed: {config.name}")
            logger.info(f"Processed: {stats['processed']}, Created: {stats['created']}, "
                       f"Updated: {stats['updated']}, Skipped: {stats['skipped']}")
            logger.info(f"{'='*70}\n")

        except Exception as e:
            logger.error(f"Scheduled sync failed: {config.name}", exc_info=True)

    def start(self):
        """Start the scheduler (blocking)."""
        if not self.scheduler.get_jobs():
            logger.warning("No jobs scheduled!")
            return

        logger.info("\n" + "="*70)
        logger.info("SYNC SCHEDULER STARTED")
        logger.info("="*70)

        # List scheduled jobs
        for job in self.scheduler.get_jobs():
            logger.info(f"  • {job.name}: {job.next_run_time}")

        logger.info("="*70 + "\n")

        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("\nScheduler stopped by user")
            self.shutdown()

    def shutdown(self):
        """Shutdown the scheduler."""
        logger.info("Shutting down scheduler...")
        self.scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")

    def run_now(self, sync_name: str):
        """
        Trigger an immediate sync run.

        Args:
            sync_name: Name of the sync to run
        """
        job_id = self._job_ids.get(sync_name)
        if job_id:
            logger.info(f"Triggering immediate run: {sync_name}")
            job = self.scheduler.get_job(job_id)
            if job:
                job.modify(next_run_time=datetime.now())
        else:
            logger.warning(f"No job found for sync: {sync_name}")

    def get_job_status(self) -> List[dict]:
        """
        Get status of all scheduled jobs.

        Returns:
            List of job status dictionaries
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs
