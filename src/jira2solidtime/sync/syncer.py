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

        # Cache for issue data (summary + Epic) to reduce API calls
        # Structure: {issue_id: {key, summary, epic_name}}
        issue_cache: dict[str, dict[str, Any]] = {}

        # Pre-fetch all unique issues in batch (performance optimization)
        logger.info("Pre-fetching issue data in batch...")
        unique_issue_ids = set()
        for worklog in worklogs:
            issue = worklog.get("issue", {})
            issue_id = issue.get("id")
            if issue_id:
                unique_issue_ids.add(str(issue_id))

        if unique_issue_ids:
            # Batch fetch with parent field for Epic support
            batch_issues = self.jira_client.get_issues_by_ids(
                list(unique_issue_ids), fields=["summary", "parent"]
            )

            # Build cache with Epic data
            for issue_id, issue_data in batch_issues.items():
                fields = issue_data.get("fields", {})
                issue_key = issue_data.get("key", "")
                issue_summary = fields.get("summary", "")

                # Extract Epic name from parent field
                epic_name = None
                parent = fields.get("parent")
                if parent:
                    parent_fields = parent.get("fields", {})
                    epic_summary = parent_fields.get("summary", "")
                    if epic_summary:
                        epic_name = epic_summary

                issue_cache[issue_id] = {
                    "key": issue_key,
                    "summary": issue_summary,
                    "epic_name": epic_name,
                }

            logger.info(
                f"Pre-fetched {len(issue_cache)} issues (found {len(batch_issues)} of {len(unique_issue_ids)})"
            )

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

                # Get issue data from pre-fetched cache
                issue_summary = ""
                epic_name = None

                if issue_id:
                    issue_id_str = str(issue_id)

                    # Check cache first (should be pre-populated from batch fetch)
                    if issue_id_str in issue_cache:
                        cached_data = issue_cache[issue_id_str]
                        issue_key = cached_data.get("key", issue_key)
                        issue_summary = cached_data.get("summary", "")
                        epic_name = cached_data.get("epic_name")
                    else:
                        # Fallback: fetch individually if not in batch (shouldn't happen often)
                        logger.debug(f"Issue {issue_id_str} not in cache, fetching individually")
                        try:
                            jira_issue = self.jira_client.get_issue(
                                issue_id_str, fields=["summary", "parent"]
                            )
                            issue_key = jira_issue.get("key", issue_key)
                            fields = jira_issue.get("fields", {})
                            issue_summary = fields.get("summary", "")

                            # Extract Epic from parent
                            parent = fields.get("parent")
                            if parent:
                                parent_fields = parent.get("fields", {})
                                epic_name = parent_fields.get("summary")

                            # Cache for future use in this sync
                            issue_cache[issue_id_str] = {
                                "key": issue_key,
                                "summary": issue_summary,
                                "epic_name": epic_name,
                            }
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

                # Build description with Epic: "Epic Name > ISSUE-KEY: Summary - comment"
                # If no Epic: "[No Epic] > ISSUE-KEY: Summary - comment"
                epic_prefix = epic_name if epic_name else "[No Epic]"
                base_desc = (
                    f"{epic_prefix} > {issue_key}: {issue_summary}"
                    if issue_summary
                    else f"{epic_prefix} > {issue_key}"
                )
                description = f"{base_desc} - {worklog_comment}" if worklog_comment else base_desc

                # Prepare date string for change detection
                date_str = work_date.strftime("%Y-%m-%dT%H:%M:%SZ")

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
                            duration_minutes=duration_minutes,
                            description=description,
                            date=date_str,
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
                    # UPDATE: Check if data changed
                    has_changes = self.mapping.has_changes(
                        tempo_worklog_id=tempo_worklog_id,
                        duration_minutes=duration_minutes,
                        description=description,
                        date_str=date_str,
                    )

                    # Performance optimization: Only UPDATE if data changed or we need to check existence
                    # Check if last existence verification was >24h ago
                    needs_existence_check = self.mapping.needs_existence_check(tempo_worklog_id)

                    if has_changes:
                        # Data changed - perform UPDATE
                        logger.debug(f"Changes detected for entry {entry_id}, updating")

                        try:
                            update_result = self.solidtime_client.update_time_entry(
                                entry_id=entry_id,
                                duration_minutes=duration_minutes,
                                date=work_date,
                                description=description,
                            )

                            if update_result and update_result.get("data"):
                                # UPDATE succeeded
                                self.mapping.mark_processed(tempo_worklog_id)
                                updated += 1
                                self.mapping.update_sync_data(
                                    tempo_worklog_id=tempo_worklog_id,
                                    duration_minutes=duration_minutes,
                                    description=description,
                                    date_str=date_str,
                                )
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

                                # CREATE as new entry (see recovery logic below)
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
                                        duration_minutes=duration_minutes,
                                        description=description,
                                        date=date_str,
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

                    elif needs_existence_check:
                        # No changes, but check existence (periodic verification)
                        logger.debug(
                            f"No changes for {issue_key}, but performing periodic existence check"
                        )

                        try:
                            update_result = self.solidtime_client.update_time_entry(
                                entry_id=entry_id,
                                duration_minutes=duration_minutes,
                                date=work_date,
                                description=description,
                            )

                            if update_result and update_result.get("data"):
                                # Entry still exists
                                self.mapping.mark_processed(tempo_worklog_id)
                                self.mapping.update_last_check(tempo_worklog_id)
                                logger.debug(f"Existence verified for {issue_key}")
                            else:
                                # Entry was deleted - recreate it
                                logger.info(
                                    f"Entry {entry_id} not found (404), removing mapping and creating new"
                                )
                                self.mapping.remove_mapping(tempo_worklog_id)

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
                                        duration_minutes=duration_minutes,
                                        description=description,
                                        date=date_str,
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
                        except Exception as e:
                            logger.error(f"Existence check failed: {e}")
                            failed += 1

                    else:
                        # No changes and recent existence check - skip UPDATE entirely
                        self.mapping.mark_processed(tempo_worklog_id)
                        logger.debug(
                            f"No changes for {issue_key}, skipping UPDATE (recently verified)"
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

        # Save mappings after Phase 1 (batch write optimization)
        logger.debug("Saving mappings after Phase 1...")
        self.mapping.save()

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

        # Save mappings after Phase 2 (batch write optimization)
        logger.debug("Saving mappings after Phase 2...")
        self.mapping.save()

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
