"""Core synchronization logic."""

import logging
from datetime import datetime, timedelta
from typing import Any

from jira2solidtime.api.jira_client import JiraClient
from jira2solidtime.api.solidtime_client import SolidtimeClient
from jira2solidtime.api.tempo_client import TempoClient
from jira2solidtime.sync.mapper import Mapper

logger = logging.getLogger(__name__)


class Syncer:
    """Orchestrates synchronization between Tempo and Solidtime."""

    def __init__(
        self,
        tempo_client: TempoClient,
        jira_client: JiraClient,
        solidtime_client: SolidtimeClient,
        mapper: Mapper,
    ) -> None:
        """Initialize syncer.

        Args:
            tempo_client: Tempo API client
            jira_client: Jira API client
            solidtime_client: Solidtime API client
            mapper: Project mapper
        """
        self.tempo_client = tempo_client
        self.jira_client = jira_client
        self.solidtime_client = solidtime_client
        self.mapper = mapper

    def sync(self, days_back: int = 30) -> dict[str, Any]:
        """Perform synchronization.

        Args:
            days_back: Number of days to sync back

        Returns:
            Sync result statistics
        """
        logger.info(f"Starting sync for last {days_back} days...")

        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days_back)

        # Fetch worklogs from Tempo
        try:
            worklogs = self.tempo_client.get_worklogs(from_date, to_date)
            logger.info(f"Found {len(worklogs)} worklogs in Tempo")
        except Exception as e:
            logger.error(f"Failed to fetch worklogs: {e}")
            return {"success": False, "error": str(e)}

        # Get Solidtime projects for mapping
        try:
            projects = self.solidtime_client.get_projects()
        except Exception as e:
            logger.error(f"Failed to fetch Solidtime projects: {e}")
            return {"success": False, "error": str(e)}

        # Sync worklogs
        created = 0
        failed = 0
        skipped = 0

        for worklog in worklogs:
            try:
                # Extract Jira issue information from Tempo worklog
                issue = worklog.get("issue", {})
                issue_id = issue.get("id")
                issue_key = issue.get("key")

                # If no key in worklog, fetch from Jira using issue ID
                if not issue_key and issue_id:
                    try:
                        jira_issue = self.jira_client.get_issue(str(issue_id))
                        issue_key = jira_issue.get("key")
                        logger.debug(f"Fetched issue key {issue_key} from Jira for ID {issue_id}")
                    except Exception as e:
                        logger.warning(f"Could not fetch issue {issue_id} from Jira: {e}")
                        skipped += 1
                        continue

                if not issue_key:
                    logger.warning(f"Could not extract issue key from worklog (ID: {issue_id})")
                    skipped += 1
                    continue

                project_key = issue_key.split("-")[0] if issue_key else None

                if not project_key:
                    logger.warning(f"Could not extract project key from {issue_key}")
                    skipped += 1
                    continue

                # Map to Solidtime project
                solidtime_project_name = self.mapper.map_project(project_key)
                if not solidtime_project_name:
                    logger.debug(f"No mapping found for {project_key}, skipping")
                    skipped += 1
                    continue

                # Find Solidtime project ID
                project_id = None
                for proj in projects:
                    if proj.get("name") == solidtime_project_name:
                        project_id = proj.get("id")
                        break

                if not project_id:
                    logger.warning(f"Could not find project {solidtime_project_name} in Solidtime")
                    skipped += 1
                    continue

                # Create time entry in Solidtime
                duration_minutes = worklog.get("timeSpentSeconds", 0) // 60

                # Parse start date and time from worklog
                start_date_str = worklog.get("startDate", "")
                start_time_str = worklog.get("startTime", "08:00:00")
                work_date = datetime.fromisoformat(f"{start_date_str}T{start_time_str}")

                description = worklog.get("comment", issue_key or "")

                self.solidtime_client.create_time_entry(
                    project_id=project_id,
                    duration_minutes=duration_minutes,
                    date=work_date,
                    description=description,
                )

                created += 1
                logger.debug(f"Created time entry for {issue_key}: {duration_minutes}m")

            except Exception as e:
                logger.error(f"Failed to sync worklog: {e}")
                failed += 1

        logger.info(f"Sync complete: created={created}, failed={failed}, skipped={skipped}")

        return {
            "success": True,
            "created": created,
            "failed": failed,
            "skipped": skipped,
            "total": len(worklogs),
            "timestamp": datetime.now().isoformat(),
        }
