"""Core synchronization logic."""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from jira2solidtime.api.jira_client import JiraClient
from jira2solidtime.api.solidtime_client import SolidtimeClient
from jira2solidtime.api.tempo_client import TempoClient
from jira2solidtime.sync.mapper import Mapper
from jira2solidtime.sync.worklog_mapping import WorklogMapping

logger = logging.getLogger(__name__)


class Syncer:
    """Orchestrates synchronization between Tempo and Solidtime."""

    def __init__(
        self,
        tempo_client: TempoClient,
        jira_client: JiraClient,
        solidtime_client: SolidtimeClient,
        mapper: Mapper,
        mapping: Optional[WorklogMapping] = None,
    ) -> None:
        """Initialize syncer.

        Args:
            tempo_client: Tempo API client
            jira_client: Jira API client
            solidtime_client: Solidtime API client
            mapper: Project mapper
            mapping: Worklog mapping tracker (creates new if None)
        """
        self.tempo_client = tempo_client
        self.jira_client = jira_client
        self.solidtime_client = solidtime_client
        self.mapper = mapper
        self.mapping = mapping or WorklogMapping()

    def sync(self, days_back: int = 30) -> dict[str, Any]:
        """Perform complete synchronization with CREATE/UPDATE/DELETE.

        Args:
            days_back: Number of days to sync back

        Returns:
            Sync result with detailed action history
        """
        logger.info(f"Starting sync for last {days_back} days...")
        start_time = datetime.now()

        # Reset processed flags for this sync run
        self.mapping.reset_processed()

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

        # Track actions for detailed reporting
        actions: list[dict[str, Any]] = []
        created = 0
        updated = 0
        deleted = 0
        failed = 0

        # Cache for issue summaries to reduce API calls
        issue_cache: dict[str, str] = {}

        # Phase 1: CREATE and UPDATE
        for worklog in worklogs:
            try:
                # Get Tempo worklog ID
                tempo_worklog_id = worklog.get("tempoWorklogId")
                if not tempo_worklog_id:
                    logger.warning("Worklog missing tempoWorklogId, skipping")
                    continue

                # Get basic info from worklog
                issue = worklog.get("issue", {})
                issue_id = issue.get("id")
                issue_key = issue.get("key")

                # Always fetch full issue to get summary (with caching)
                issue_summary = ""
                if issue_id:
                    issue_id_str = str(issue_id)

                    # Check cache first
                    if issue_id_str in issue_cache:
                        issue_summary = issue_cache[issue_id_str]
                        # Use cached issue_key if we don't have one
                        if not issue_key:
                            # Issue key format: extract from cached data or construct
                            # For now, we need to fetch if key is missing
                            pass

                    # Fetch from Jira if not cached or key missing
                    if not issue_key or issue_id_str not in issue_cache:
                        try:
                            jira_issue = self.jira_client.get_issue(issue_id_str)
                            issue_key = jira_issue.get("key", issue_key)
                            issue_summary = jira_issue.get("fields", {}).get("summary", "")
                            # Cache the summary
                            issue_cache[issue_id_str] = issue_summary
                        except Exception as e:
                            logger.warning(f"Could not fetch issue {issue_id}: {e}")
                            failed += 1
                            continue

                if not issue_key:
                    logger.warning(f"No issue key for worklog {tempo_worklog_id}")
                    failed += 1
                    continue

                # Get project info
                project_key = issue_key.split("-")[0]
                solidtime_project_name = self.mapper.map_project(project_key)
                if not solidtime_project_name:
                    logger.debug(f"No mapping for project {project_key}")
                    continue

                project_id = next(
                    (p.get("id") for p in projects if p.get("name") == solidtime_project_name),
                    None,
                )
                if not project_id:
                    logger.warning(f"Project {solidtime_project_name} not in Solidtime")
                    failed += 1
                    continue

                # Prepare time entry data
                duration_minutes = worklog.get("timeSpentSeconds", 0) // 60
                start_date_str = worklog.get("startDate", "")
                start_time_str = worklog.get("startTime", "08:00:00")
                work_date = datetime.fromisoformat(f"{start_date_str}T{start_time_str}")

                # Tempo uses "description" field for worklog comments, not "comment"
                worklog_comment = worklog.get("description", "")

                # Build description: "ISSUE-KEY: Summary" or "ISSUE-KEY: Summary - comment"
                base_desc = f"{issue_key}: {issue_summary}" if issue_summary else issue_key
                description = f"{base_desc} - {worklog_comment}" if worklog_comment else base_desc

                # Check if already synced (CREATE vs UPDATE)
                entry_id = self.mapping.get_solidtime_entry_id(tempo_worklog_id)

                if not entry_id:
                    # CREATE: New worklog
                    result = self.solidtime_client.create_time_entry(
                        project_id=project_id,
                        duration_minutes=duration_minutes,
                        date=work_date,
                        description=description,
                    )

                    new_entry_id = result.get("data", {}).get("id")
                    if new_entry_id:
                        self.mapping.add_mapping(
                            tempo_worklog_id=str(tempo_worklog_id),
                            solidtime_entry_id=new_entry_id,
                            issue_key=issue_key,
                        )
                        created += 1
                        self.mapping.mark_processed(tempo_worklog_id)
                        actions.append(
                            {
                                "action": "CREATE",
                                "issue_key": issue_key,
                                "worklog_comment": worklog_comment,
                                "duration_minutes": duration_minutes,
                                "status": "success",
                            }
                        )
                        logger.debug(f"Created entry for {issue_key}: {duration_minutes}m")
                    else:
                        failed += 1
                        actions.append(
                            {
                                "action": "CREATE",
                                "issue_key": issue_key,
                                "worklog_comment": worklog_comment,
                                "duration_minutes": duration_minutes,
                                "status": "failed",
                                "error": "No entry ID in response",
                            }
                        )
                else:
                    # UPDATE: Try to update existing entry
                    # Note: We can't use GET to check existence (403 Forbidden)
                    # Instead, we try UPDATE and handle 404 if entry was deleted
                    logger.debug(f"Attempting UPDATE for entry {entry_id}")

                    try:
                        update_result = self.solidtime_client.update_time_entry(
                            entry_id=entry_id,
                            duration_minutes=duration_minutes,
                            date=work_date,
                            description=description,
                        )

                        if update_result and update_result.get("data"):
                            # UPDATE succeeded
                            updated += 1
                            self.mapping.mark_processed(tempo_worklog_id)
                            actions.append(
                                {
                                    "action": "UPDATE",
                                    "issue_key": issue_key,
                                    "worklog_comment": worklog_comment,
                                    "duration_minutes": duration_minutes,
                                    "status": "success",
                                }
                            )
                            logger.debug(f"Updated entry for {issue_key}: {duration_minutes}m")
                        else:
                            # UPDATE returned None (404) - entry was deleted manually
                            logger.info(
                                f"Entry {entry_id} not found (404), removing mapping and creating new"
                            )
                            self.mapping.remove_mapping(tempo_worklog_id)

                            # CREATE as new entry
                            create_result = self.solidtime_client.create_time_entry(
                                project_id=project_id,
                                duration_minutes=duration_minutes,
                                date=work_date,
                                description=description,
                            )

                            new_entry_id = create_result.get("data", {}).get("id")
                            if new_entry_id:
                                self.mapping.add_mapping(
                                    tempo_worklog_id=str(tempo_worklog_id),
                                    solidtime_entry_id=new_entry_id,
                                    issue_key=issue_key,
                                )
                                created += 1
                                self.mapping.mark_processed(tempo_worklog_id)
                                actions.append(
                                    {
                                        "action": "CREATE",
                                        "issue_key": issue_key,
                                        "worklog_comment": worklog_comment,
                                        "duration_minutes": duration_minutes,
                                        "status": "success",
                                        "reason": "Recovered after manual delete",
                                    }
                                )
                                logger.debug(
                                    f"Recovered entry for {issue_key}: {duration_minutes}m"
                                )
                            else:
                                failed += 1
                                actions.append(
                                    {
                                        "action": "RECOVER",
                                        "issue_key": issue_key,
                                        "worklog_comment": worklog_comment,
                                        "duration_minutes": duration_minutes,
                                        "status": "failed",
                                        "error": "Recovery failed - no entry ID",
                                    }
                                )
                    except Exception as e:
                        # Unexpected error during UPDATE
                        logger.error(f"UPDATE failed with exception: {e}")
                        failed += 1
                        actions.append(
                            {
                                "action": "UPDATE",
                                "issue_key": issue_key,
                                "worklog_comment": worklog_comment,
                                "duration_minutes": duration_minutes,
                                "status": "failed",
                                "error": str(e),
                            }
                        )

            except Exception as e:
                logger.error(f"Failed to sync worklog: {e}")
                failed += 1
                actions.append(
                    {
                        "action": "ERROR",
                        "issue_key": issue_key if "issue_key" in locals() else "UNKNOWN",
                        "status": "failed",
                        "error": str(e),
                    }
                )

        # Phase 2: DELETE (Overhang cleanup)
        for tempo_id, mapping in self.mapping.get_unprocessed_mappings():
            try:
                entry_id = mapping.get("solidtime_entry_id")
                issue_key = mapping.get("issue_key", "UNKNOWN")

                if entry_id and self.solidtime_client.delete_time_entry(entry_id):
                    deleted += 1
                    self.mapping.remove_mapping(tempo_id)
                    actions.append(
                        {
                            "action": "DELETE",
                            "issue_key": issue_key,
                            "status": "success",
                            "reason": "Worklog deleted from Tempo",
                        }
                    )
                    logger.debug(f"Deleted entry {entry_id} for {issue_key}")
                else:
                    failed += 1
                    actions.append(
                        {
                            "action": "DELETE",
                            "issue_key": issue_key,
                            "status": "failed",
                            "error": "Delete failed",
                        }
                    )

            except Exception as e:
                logger.error(f"Failed to delete entry: {e}")
                failed += 1

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Sync complete: created={created}, updated={updated}, deleted={deleted}, "
            f"failed={failed} ({duration:.1f}s)"
        )

        return {
            "success": True,
            "created": created,
            "updated": updated,
            "deleted": deleted,
            "failed": failed,
            "total": len(worklogs),
            "actions": actions,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
        }
