"""Core synchronization service."""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from ..domain.models import SyncRequest, SyncResult
from ..api.tempo_client import TempoClient
from ..api.jira_client import JiraClient
from ..api.solidtime_client import SolidtimeClient
from ..mapping.field_mapper import FieldMapper
from ..utils.worklog_mapping import WorklogMapping
from ..sync.issue_comparator import IssueComparator
from ..cli.progress import ModernCLI
from ..utils.logging import StructuredLogger
from ..monitoring.metrics_exporter import MetricsExporter
from ..monitoring.health_check import HealthChecker

logger = logging.getLogger(__name__)


class SyncService:
    """Service for handling worklog synchronization between Tempo and Solidtime."""

    def __init__(
        self,
        tempo_client: TempoClient,
        jira_client: JiraClient,
        solidtime_client: SolidtimeClient,
        field_mapper: FieldMapper,
        worklog_mapping: WorklogMapping,
        logger: StructuredLogger,
        metrics_exporter: Optional[MetricsExporter] = None,
    ):
        self.tempo_client = tempo_client
        self.jira_client = jira_client
        self.solidtime_client = solidtime_client
        self.field_mapper = field_mapper
        self.worklog_mapping = worklog_mapping
        self.logger = logger
        self.comparator = IssueComparator(worklog_mapping)
        self.metrics_exporter = metrics_exporter
        self.health_checker = HealthChecker(tempo_client, solidtime_client)

    def sync_worklogs(
        self, request: SyncRequest, cli: ModernCLI, filter_user: Optional[str] = None
    ) -> SyncResult:
        """Synchronize worklogs from Tempo to Solidtime."""

        # Fetch Tempo worklogs
        with cli.progress_spinner("Fetching Tempo worklogs..."):
            tempo_worklogs = self.tempo_client.get_filtered_worklogs(
                request.start_date,
                request.end_date,
                filter_user,
                request.project_keys,
                None,
                self.jira_client,
            )

        if not tempo_worklogs:
            return SyncResult.empty()

        # Fetch existing Solidtime entries
        with cli.progress_spinner("Fetching Solidtime entries..."):
            solidtime_entries = self.solidtime_client.get_all_time_entries(
                request.start_date, request.end_date
            )

        # Generate worklog-level sync plan
        with cli.progress_spinner("Analyzing changes..."):
            (
                worklogs_to_create,
                worklogs_to_update,
                entry_ids_to_delete,
                entry_ids_to_update,
                plan,
            ) = self.comparator.detailed_worklog_sync_plan(
                tempo_worklogs, solidtime_entries
            )

        # Prepare results
        result_data = {
            "total_entries": len(tempo_worklogs),
            "changes": plan["worklogs_to_create"]
            + plan["worklogs_to_update"]
            + plan["entries_to_delete"],
            "created": plan["worklogs_to_create"],
            "updated": plan["worklogs_to_update"],
            "deleted": plan["entries_to_delete"],
            "total_hours": sum(
                worklog.get("timeSpentSeconds", 0) / 3600 for worklog in tempo_worklogs
            ),
            "worklog_details": {"created": [], "updated": [], "deleted": []},
        }

        # If dry run or no changes, return early
        if request.dry_run or result_data["changes"] == 0:
            return SyncResult(**result_data)

        # Perform actual sync operations
        (
            successful_creates,
            successful_updates,
            successful_deletes,
        ) = self._execute_sync_operations(
            worklogs_to_create,
            worklogs_to_update,
            entry_ids_to_delete,
            entry_ids_to_update,
            solidtime_entries,
            result_data,
            cli,
        )

        # Update final results
        result_data.update(
            {
                "created": successful_creates,
                "updated": successful_updates,
                "deleted": successful_deletes,
            }
        )

        result = SyncResult(**result_data)

        # Export metrics if exporter is available
        if self.metrics_exporter:
            # Duration will be calculated in main.py and passed here
            self.metrics_exporter.export_sync_metrics(result, 0, "success")

        return result

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all external dependencies."""
        health_status = self.health_checker.check_all()

        # Export health metrics if exporter is available
        if self.metrics_exporter:
            tempo_healthy = health_status["tempo"]["status"] == "healthy"
            solidtime_healthy = health_status["solidtime"]["status"] == "healthy"
            self.metrics_exporter.export_health_metrics(
                tempo_healthy, solidtime_healthy
            )

        return health_status

    def _execute_sync_operations(
        self,
        worklogs_to_create: List[Dict],
        worklogs_to_update: List[Dict],
        entry_ids_to_delete: List[str],
        entry_ids_to_update: List[str],
        solidtime_entries: List[Dict],
        result_data: Dict[str, Any],
        cli: ModernCLI,
    ) -> tuple[int, int, int]:
        """Execute the actual sync operations and return success counts."""

        successful_creates = self._handle_deletions(
            entry_ids_to_delete, solidtime_entries, result_data, cli
        )
        successful_updates = self._handle_creations(
            worklogs_to_create, result_data, cli
        )
        successful_deletes = self._handle_updates(
            worklogs_to_update, entry_ids_to_update, solidtime_entries, result_data, cli
        )

        return successful_creates, successful_updates, successful_deletes

    def _handle_deletions(
        self,
        entry_ids_to_delete: List[str],
        solidtime_entries: List[Dict],
        result_data: Dict[str, Any],
        cli: ModernCLI,
    ) -> int:
        """Handle deletion of Solidtime entries."""
        if not entry_ids_to_delete:
            return 0

        successful_deletes = 0
        existing_entries_lookup = {
            entry.get("id"): entry for entry in solidtime_entries if entry.get("id")
        }

        with cli.progress_spinner(f"Deleting {len(entry_ids_to_delete)} entries..."):
            for entry_id in entry_ids_to_delete:
                if self.solidtime_client.delete_time_entry(entry_id):
                    successful_deletes += 1
                    self._add_deletion_details(
                        entry_id, existing_entries_lookup, result_data
                    )

        return successful_deletes

    def _handle_creations(
        self,
        worklogs_to_create: List[Dict],
        result_data: Dict[str, Any],
        cli: ModernCLI,
    ) -> int:
        """Handle creation of new Solidtime entries."""
        if not worklogs_to_create:
            return 0

        # Map worklogs for creation
        mapped_worklogs = self.field_mapper.map_multiple_worklogs(worklogs_to_create)

        # Get member_id and project mapping
        member_id, project_mapping = self._get_solidtime_mappings()
        if not member_id:
            return 0

        # Convert and create time entries
        time_entries = self._convert_worklogs_to_time_entries(
            mapped_worklogs, project_mapping, member_id
        )

        if not time_entries:
            return 0

        with cli.progress_spinner(f"Creating {len(time_entries)} entries..."):
            creation_results = self.solidtime_client.bulk_create_time_entries(
                time_entries
            )
            successful_creates = len([r for r in creation_results if r["success"]])

        # Save worklog mappings and collect details for display
        self._process_creation_results(
            creation_results, worklogs_to_create, result_data
        )

        return successful_creates

    def _handle_updates(
        self,
        worklogs_to_update: List[Dict],
        entry_ids_to_update: List[str],
        solidtime_entries: List[Dict],
        result_data: Dict[str, Any],
        cli: ModernCLI,
    ) -> int:
        """Handle updates of existing Solidtime entries."""
        if not worklogs_to_update or not entry_ids_to_update:
            return 0

        successful_updates = 0
        member_id, project_mapping = self._get_solidtime_mappings()
        if not member_id:
            return 0

        existing_entries = {
            entry.get("id"): entry for entry in solidtime_entries if entry.get("id")
        }

        with cli.progress_spinner(f"Updating {len(entry_ids_to_update)} entries..."):
            for i, tempo_worklog in enumerate(worklogs_to_update):
                if i < len(entry_ids_to_update):
                    if self._update_single_entry(
                        tempo_worklog,
                        entry_ids_to_update[i],
                        existing_entries,
                        project_mapping,
                        member_id,
                        worklogs_to_update,
                        i,
                        result_data,
                    ):
                        successful_updates += 1

        # Save updated mappings
        self.comparator.worklog_mapping.save_mappings()
        return successful_updates

    def _get_solidtime_mappings(self) -> tuple[Optional[str], Dict[str, str]]:
        """Get member_id and project mapping for Solidtime operations."""
        memberships = self.solidtime_client.get_user_memberships()
        member_id = None

        for membership in memberships:
            if (
                membership.get("organization", {}).get("id")
                == self.solidtime_client.organization_id
            ):
                member_id = membership.get("id")
                break

        projects_data = self.solidtime_client.get_projects()
        project_mapping = {
            proj.get("name", ""): proj.get("id", "")
            for proj in projects_data
            if proj.get("id")
        }

        return member_id, project_mapping

    def _convert_worklogs_to_time_entries(
        self,
        mapped_worklogs: List[Dict],
        project_mapping: Dict[str, str],
        member_id: str,
    ) -> List[Dict]:
        """Convert worklogs to time entries."""
        time_entries = []
        for worklog in mapped_worklogs:
            try:
                time_entry = self.solidtime_client.convert_worklog_to_time_entry(
                    worklog, project_mapping, {}, member_id
                )
                time_entries.append(time_entry)
            except (KeyError, ValueError, TypeError) as e:
                # Skip malformed worklog entries but log the issue
                logger.warning(f"Skipping malformed worklog entry: {e}")
                continue
        return time_entries

    def _add_deletion_details(
        self,
        entry_id: str,
        existing_entries_lookup: Dict[Any, Dict],
        result_data: Dict[str, Any],
    ) -> None:
        """Add details for deleted entry to results."""
        existing_entry = existing_entries_lookup.get(entry_id)
        if not existing_entry:
            return

        # Extract issue info from description [JiraSync:ID] pattern
        description = existing_entry.get("description", "")
        issue_key = ""
        summary = "Deleted entry"

        # Parse description to extract issue key and summary
        if ":" in description and "[JiraSync:" in description:
            parts = description.split(":", 1)
            if len(parts) >= 2:
                issue_key = parts[0].strip()
                summary_part = parts[1].split("[JiraSync:")[0].strip()
                if summary_part:
                    summary = summary_part

        # Calculate duration from start/end times
        duration_hours = self._calculate_duration_from_entry(existing_entry)

        result_data["worklog_details"]["deleted"].append(
            {
                "issue_key": issue_key,
                "summary": summary,
                "description": description,
                "duration_hours": duration_hours,
            }
        )

    def _process_creation_results(
        self,
        creation_results: List[Dict],
        worklogs_to_create: List[Dict],
        result_data: Dict[str, Any],
    ) -> None:
        """Process creation results and update mappings."""
        for i, result in enumerate(creation_results):
            if result["success"] and i < len(worklogs_to_create):
                tempo_worklog = worklogs_to_create[i]
                entry_data = result.get("data", {})
                new_entry_id = (
                    entry_data.get("data", {}).get("id") if entry_data else None
                )

                if new_entry_id:
                    # Set current timestamp as solidtime_updated_at since we just created it
                    current_time = datetime.now().isoformat() + "Z"
                    self.comparator.add_worklog_mapping(
                        tempo_worklog, new_entry_id, current_time
                    )

                    # Add to detailed results for table display
                    issue_info = tempo_worklog.get("issue", {})
                    tempo_desc = tempo_worklog.get("description", "")
                    tempo_id = tempo_worklog.get("tempoWorklogId", "")
                    solidtime_formatted_desc = f"{issue_info.get('key', '')}: {tempo_desc} [JiraSync:{tempo_id}]"

                    result_data["worklog_details"]["created"].append(
                        {
                            "issue_key": issue_info.get("key", ""),
                            "summary": issue_info.get("summary", "No description"),
                            "description": solidtime_formatted_desc,
                            "duration_hours": tempo_worklog.get("timeSpentSeconds", 0)
                            / 3600.0,
                        }
                    )

    def _update_single_entry(
        self,
        tempo_worklog: Dict,
        entry_id: str,
        existing_entries: Dict[Any, Dict],
        project_mapping: Dict[str, str],
        member_id: str,
        worklogs_to_update: List[Dict],
        index: int,
        result_data: Dict[str, Any],
    ) -> bool:
        """Update a single entry and return success status."""
        existing_entry = existing_entries.get(entry_id)
        if not existing_entry:
            self.logger.log_api_error(
                "sync", f"Could not find existing entry {entry_id} for update"
            )
            return False

        try:
            # For updates, preserve existing project_id and task_id to avoid mapping issues
            existing_project_id = existing_entry.get("project_id")
            existing_task_id = existing_entry.get("task_id")

            # Use field mapper for consistent project/task mapping
            mapped_tempo = self.field_mapper.map_tempo_worklog(tempo_worklog)
            time_entry_data = self.solidtime_client.convert_worklog_to_time_entry(
                mapped_tempo, project_mapping, {}, member_id
            )

            # Override description with TEMPO data (SSoT)
            issue_key = tempo_worklog.get("issue", {}).get("key", "")
            tempo_description = tempo_worklog.get("description", "")
            tempo_worklog_id = tempo_worklog.get("tempoWorklogId", "")
            time_entry_data["description"] = (
                f"{issue_key}: {tempo_description} [JiraSync:{tempo_worklog_id}]"
            )

            # Override with existing project/task IDs to avoid mapping conflicts
            if existing_project_id:
                time_entry_data["project_id"] = existing_project_id
            if existing_task_id:
                time_entry_data["task_id"] = existing_task_id

            # Use proper UPDATE API call
            updated_entry = self.solidtime_client.update_time_entry(
                entry_id, time_entry_data
            )
            if updated_entry:
                self._update_mapping_and_details(
                    tempo_worklog,
                    worklogs_to_update,
                    index,
                    existing_entry,
                    result_data,
                )
                return True
            else:
                self.logger.log_api_error(
                    "solidtime", f"Failed to update entry {entry_id}"
                )
                return False

        except Exception as e:
            self.logger.log_api_error(
                "solidtime", f"Failed to update entry {entry_id}: {e}"
            )
            return False

    def _update_mapping_and_details(
        self,
        tempo_worklog: Dict,
        worklogs_to_update: List[Dict],
        index: int,
        existing_entry: Dict,
        result_data: Dict[str, Any],
    ) -> None:
        """Update mapping and add details for updated entry."""
        # Update mapping with latest timestamps
        current_tempo_worklog = worklogs_to_update[index]
        tempo_id = str(current_tempo_worklog.get("tempoWorklogId", ""))
        self.comparator.worklog_mapping.mappings[tempo_id]["tempo_updated_at"] = (
            current_tempo_worklog.get("updatedAt", "")
        )
        self.comparator.worklog_mapping.mappings[tempo_id]["solidtime_updated_at"] = (
            datetime.now().isoformat() + "Z"
        )
        self.comparator.worklog_mapping.clear_update_flag(tempo_id)

        # Add change detection and detailed results
        issue_info = current_tempo_worklog.get("issue", {})
        old_description = existing_entry.get("description", "")
        new_tempo_desc = current_tempo_worklog.get("description", "")
        new_tempo_id = current_tempo_worklog.get("tempoWorklogId", "")
        new_solidtime_formatted_desc = (
            f"{issue_info.get('key', '')}: {new_tempo_desc} [JiraSync:{new_tempo_id}]"
        )

        # Check for description changes
        description_changed = old_description != new_solidtime_formatted_desc
        display_description = (
            f"* {new_solidtime_formatted_desc}"
            if description_changed
            else new_solidtime_formatted_desc
        )

        # Calculate duration changes
        old_duration_hours = self._calculate_duration_from_entry(existing_entry)
        new_duration_hours = current_tempo_worklog.get("timeSpentSeconds", 0) / 3600.0
        duration_changed = abs(old_duration_hours - new_duration_hours) > 0.01

        result_data["worklog_details"]["updated"].append(
            {
                "issue_key": issue_info.get("key", ""),
                "summary": issue_info.get("summary", "No description"),
                "description": display_description,
                "duration_hours": new_duration_hours,
                "old_duration_hours": old_duration_hours if duration_changed else None,
                "description_changed": description_changed,
                "duration_changed": duration_changed,
            }
        )

    def _calculate_duration_from_entry(self, entry: Dict) -> float:
        """Calculate duration in hours from start/end times."""
        duration_hours = 0.0
        start_str = entry.get("start", "")
        end_str = entry.get("end", "")

        if start_str and end_str:
            try:
                start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                duration_seconds = (end_time - start_time).total_seconds()
                duration_hours = duration_seconds / 3600.0
            except (ValueError, TypeError) as e:
                # Invalid datetime format, use fallback duration
                logger.warning(f"Invalid datetime format in worklog: {e}")
                pass

        return duration_hours
