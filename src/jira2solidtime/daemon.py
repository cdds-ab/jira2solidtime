"""Background daemon for scheduled synchronization."""

import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler

from jira2solidtime.api.jira_client import JiraClient
from jira2solidtime.api.solidtime_client import SolidtimeClient
from jira2solidtime.api.tempo_client import TempoClient
from jira2solidtime.config import Config
from jira2solidtime.history import History
from jira2solidtime.sync.mapper import Mapper
from jira2solidtime.sync.syncer import Syncer

logger = logging.getLogger(__name__)


class SyncDaemon:
    """Manages scheduled synchronization."""

    def __init__(self, config: Config) -> None:
        """Initialize daemon.

        Args:
            config: Application configuration
        """
        self.config = config
        self.scheduler = BackgroundScheduler()
        self.history = History()

        # Initialize API clients
        self.tempo_client = TempoClient(self.config.tempo["api_token"])
        self.jira_client = JiraClient(
            self.config.jira["base_url"],
            self.config.jira["user_email"],
            self.config.jira["api_token"],
        )
        self.solidtime_client = SolidtimeClient(
            self.config.solidtime["base_url"],
            self.config.solidtime["api_token"],
            self.config.solidtime["organization_id"],
        )

        # Initialize mapper
        self.mapper = Mapper(self.config.mappings)

        # Initialize syncer
        self.syncer = Syncer(
            self.tempo_client,
            self.jira_client,
            self.solidtime_client,
            self.mapper,
        )

    def _sync_job(self) -> None:
        """Execute a sync job."""
        logger.info("Starting scheduled sync job...")
        start_time = time.time()

        try:
            result = self.syncer.sync(days_back=self.config.sync.get("days_back", 30))

            duration = time.time() - start_time

            if result.get("success"):
                self.history.record_sync(
                    success=True,
                    created=result.get("created", 0),
                    failed=result.get("failed", 0),
                    skipped=result.get("skipped", 0),
                    total=result.get("total", 0),
                    duration_seconds=duration,
                )
                logger.info(
                    f"Sync completed in {duration:.2f}s: "
                    f"created={result['created']}, failed={result['failed']}, "
                    f"skipped={result['skipped']}"
                )
            else:
                self.history.record_sync(
                    success=False,
                    error=result.get("error", "Unknown error"),
                    duration_seconds=duration,
                )
                logger.error(f"Sync failed: {result.get('error')}")

        except Exception as e:
            duration = time.time() - start_time
            self.history.record_sync(
                success=False,
                error=str(e),
                duration_seconds=duration,
            )
            logger.error(f"Sync job failed with exception: {e}")

    def start(self) -> None:
        """Start the daemon."""
        logger.info("Starting SyncDaemon...")

        # Get schedule from config (cron format)
        schedule = self.config.sync.get("schedule", "0 8 * * *")
        logger.info(f"Scheduling sync with cron: {schedule}")

        # Add scheduled job
        self.scheduler.add_job(
            self._sync_job,
            "cron",
            **self._parse_cron(schedule),
            id="sync_job",
            name="Tempo to Solidtime sync",
        )

        # Start scheduler
        self.scheduler.start()
        logger.info("SyncDaemon started")

    def stop(self) -> None:
        """Stop the daemon."""
        logger.info("Stopping SyncDaemon...")
        self.scheduler.shutdown(wait=True)
        logger.info("SyncDaemon stopped")

    def sync_now(self) -> dict:
        """Execute sync immediately.

        Returns:
            Sync result
        """
        logger.info("Manual sync triggered")
        return self.syncer.sync(days_back=self.config.sync.get("days_back", 30))

    @staticmethod
    def _parse_cron(cron_string: str) -> dict:
        """Parse cron string to APScheduler kwargs.

        Args:
            cron_string: Cron format string (minute hour day month day_of_week)

        Returns:
            Dictionary for APScheduler
        """
        parts = cron_string.split()
        if len(parts) != 5:
            logger.warning(f"Invalid cron format: {cron_string}, using daily at 8 AM")
            return {"hour": 8, "minute": 0}

        minute, hour, day, month, day_of_week = parts

        return {
            "minute": minute if minute != "*" else 0,
            "hour": hour if hour != "*" else "*",
            "day": day if day != "*" else "*",
            "month": month if month != "*" else "*",
            "day_of_week": day_of_week if day_of_week != "*" else "*",
        }
