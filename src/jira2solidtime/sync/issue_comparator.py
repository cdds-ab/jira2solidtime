from typing import Dict, List, Set, Tuple, Any, Optional
import logging
from collections import defaultdict
import re

from ..utils.worklog_mapping import WorklogMapping

logger = logging.getLogger(__name__)


class IssueComparator:
    """Compare Tempo and Solidtime data to determine what needs syncing."""

    def __init__(self, worklog_mapping: Optional[WorklogMapping] = None):
        self.worklog_mapping = worklog_mapping or WorklogMapping()

    def group_tempo_worklogs_by_issue(
        self, tempo_worklogs: List[Dict]
    ) -> Dict[str, Dict]:
        """Group Tempo worklogs by issue key and calculate summary."""
        issue_data: Dict[str, Dict] = defaultdict(
            lambda: {
                "worklogs": [],
                "total_minutes": 0,
                "count": 0,
                "last_updated": None,
            }
        )

        for worklog in tempo_worklogs:
            issue_key = worklog.get("issue", {}).get("key", "")
            if not issue_key:
                continue

            # Get updated timestamp (newest one wins)
            updated_at = worklog.get("updatedAt", "")
            if updated_at and (
                not issue_data[issue_key]["last_updated"]
                or updated_at > issue_data[issue_key]["last_updated"]
            ):
                issue_data[issue_key]["last_updated"] = updated_at

            # Add to summary
            duration_seconds = worklog.get("timeSpentSeconds", 0)
            issue_data[issue_key]["worklogs"].append(worklog)
            issue_data[issue_key]["total_minutes"] += duration_seconds // 60
            issue_data[issue_key]["count"] += 1

        logger.info(
            f"Grouped {len(tempo_worklogs)} worklogs into {len(issue_data)} issues"
        )
        return dict(issue_data)

    def group_solidtime_entries_by_issue(
        self, solidtime_entries: List[Dict]
    ) -> Dict[str, Dict]:
        """Group Solidtime [JiraSync] entries by issue key and calculate summary."""
        issue_data: Dict[str, Dict] = defaultdict(
            lambda: {"entries": [], "total_minutes": 0, "count": 0}
        )

        for entry in solidtime_entries:
            description = entry.get("description", "")

            # Extract issue key from description "AS-1: something [JiraSync:610]" or "AS-1: something [JiraSync]"
            if "[JiraSync" in description:
                # Find issue key pattern at start of description
                match = re.match(r"^([A-Z]+-\d+):", description)
                if match:
                    issue_key = match.group(1)

                    # Calculate duration from duration field (in seconds)
                    duration_seconds = entry.get("duration", 0)
                    minutes = duration_seconds // 60

                    # Store entry with metadata
                    entry_data = {
                        "id": entry.get("id"),
                        "start": entry.get("start"),
                        "end": entry.get("end"),
                        "duration": duration_seconds,
                        "description": description,
                        "minutes": minutes,
                    }

                    issue_data[issue_key]["entries"].append(entry_data)
                    issue_data[issue_key]["total_minutes"] += minutes
                    issue_data[issue_key]["count"] += 1

        logger.info(
            f"Grouped {len(solidtime_entries)} Solidtime entries into {len(issue_data)} issues"
        )
        return dict(issue_data)

    def find_issues_to_sync(
        self, tempo_issues: Dict[str, Dict], solidtime_issues: Dict[str, Dict]
    ) -> Set[str]:
        """Find issues that need syncing based on Tempo changes only."""
        issues_to_sync = set()

        # Check all Tempo issues
        for issue_key, tempo_data in tempo_issues.items():
            tempo_count = tempo_data["count"]
            tempo_minutes = tempo_data["total_minutes"]
            tempo_last_updated = tempo_data.get("last_updated", "")

            if issue_key in solidtime_issues:
                solidtime_data = solidtime_issues[issue_key]
                solidtime_count = solidtime_data["count"]
                solidtime_minutes = solidtime_data["total_minutes"]

                # Smart comparison: Only sync if Tempo has MORE worklogs or equal with newer timestamp
                # This prevents re-syncing when user manually deletes Solidtime entries
                should_sync = False

                if tempo_count > solidtime_count:
                    # New worklogs in Tempo - but don't delete existing ones
                    should_sync = True
                    reason = f"New worklogs: Tempo({tempo_count}w) > Solidtime({solidtime_count}e)"
                elif (
                    tempo_count == solidtime_count
                    and tempo_minutes != solidtime_minutes
                ):
                    # Same count but different time - worklog was updated
                    should_sync = True
                    reason = f"Updated worklogs: Tempo({tempo_minutes}m) != Solidtime({solidtime_minutes}m)"
                elif tempo_count < solidtime_count:
                    # Fewer worklogs in Tempo - could be Tempo deletion or manual Solidtime addition
                    # Only sync if we have a recent Tempo update timestamp
                    if tempo_last_updated:
                        should_sync = True
                        reason = f"Tempo worklogs reduced: Tempo({tempo_count}w) < Solidtime({solidtime_count}e) with recent updates"
                    else:
                        reason = f"Ignoring reduction: Tempo({tempo_count}w) < Solidtime({solidtime_count}e) - likely manual deletion"

                if should_sync:
                    logger.info(f"Issue {issue_key} changed: {reason}")
                    issues_to_sync.add(issue_key)
                else:
                    logger.debug(
                        f"Issue {issue_key} unchanged: {reason if 'reason' in locals() else 'no changes detected'}"
                    )
            else:
                # New issue - needs sync
                logger.info(
                    f"New issue {issue_key}: {tempo_count} worklogs, {tempo_minutes} minutes"
                )
                issues_to_sync.add(issue_key)

        # Check for deleted issues (exist in Solidtime but not in Tempo)
        for issue_key in solidtime_issues:
            if issue_key not in tempo_issues:
                logger.info(
                    f"Issue {issue_key} deleted from Tempo - will be removed from Solidtime"
                )
                issues_to_sync.add(issue_key)

        logger.info(
            f"Found {len(issues_to_sync)} issues that need syncing: {', '.join(sorted(issues_to_sync))}"
        )
        return issues_to_sync

    def get_sync_plan(
        self,
        tempo_issues: Dict[str, Dict],
        solidtime_issues: Dict[str, Dict],
        issues_to_sync: Set[str],
    ) -> Dict:
        """Generate detailed sync plan."""
        plan: Dict[str, Any] = {
            "total_tempo_issues": len(tempo_issues),
            "total_solidtime_issues": len(solidtime_issues),
            "issues_to_sync": len(issues_to_sync),
            "unchanged_issues": len(tempo_issues) - len(issues_to_sync),
            "new_issues": [],
            "changed_issues": [],
            "deleted_issues": [],
        }

        for issue_key in issues_to_sync:
            if issue_key in tempo_issues and issue_key in solidtime_issues:
                plan["changed_issues"].append(issue_key)
            elif issue_key in tempo_issues:
                plan["new_issues"].append(issue_key)
            else:
                plan["deleted_issues"].append(issue_key)

        return plan

    def get_solidtime_entries_to_delete(
        self,
        solidtime_issues: Dict[str, Dict],
        issues_to_sync: Set[str],
        tempo_issues: Dict[str, Dict],
    ) -> List[str]:
        """Get list of Solidtime entry IDs that need to be deleted for changed issues."""
        entry_ids_to_delete = []

        for issue_key in issues_to_sync:
            if issue_key in solidtime_issues:
                tempo_count = tempo_issues.get(issue_key, {}).get("count", 0)
                solidtime_count = solidtime_issues[issue_key]["count"]

                # Only delete ALL entries if we need to recreate everything
                # (e.g., when time changed but count is same, or when Tempo has fewer worklogs)
                if tempo_count <= solidtime_count:
                    # Delete all entries for complete recreation
                    for entry in solidtime_issues[issue_key]["entries"]:
                        entry_id = entry.get("id")
                        if entry_id:
                            entry_ids_to_delete.append(entry_id)
                            logger.debug(
                                f"Will delete entry {entry_id} for complete recreation of {issue_key}"
                            )
                # If tempo_count > solidtime_count, don't delete existing entries
                # Just let new worklogs be added

        logger.info(f"Found {len(entry_ids_to_delete)} Solidtime entries to delete")
        return entry_ids_to_delete

    def get_missing_worklogs_count(
        self,
        tempo_issues: Dict[str, Dict],
        solidtime_issues: Dict[str, Dict],
        issue_key: str,
    ) -> int:
        """Calculate how many worklogs are missing for an issue."""
        tempo_count = tempo_issues.get(issue_key, {}).get("count", 0)
        solidtime_count = solidtime_issues.get(issue_key, {}).get("count", 0)
        return max(0, tempo_count - solidtime_count)

    def find_missing_worklogs(
        self, tempo_worklogs: List[Dict], solidtime_entries: List[Dict], issue_key: str
    ) -> List[Dict]:
        """Find which specific Tempo worklogs are missing in Solidtime by comparing time and duration."""
        issue_tempo_worklogs = [
            wl
            for wl in tempo_worklogs
            if wl.get("issue", {}).get("key", "") == issue_key
        ]
        issue_solidtime_entries = [
            e
            for e in solidtime_entries
            if "[JiraSync]" in e.get("description", "")
            and issue_key in e.get("description", "")
        ]

        missing_worklogs = []

        for tempo_worklog in issue_tempo_worklogs:
            # Extract worklog characteristics for matching
            tempo_duration = (
                tempo_worklog.get("timeSpentSeconds", 0) // 60
            )  # Convert to minutes
            tempo_started = tempo_worklog.get("startDate", "")  # YYYY-MM-DD format

            # Check if this worklog exists in Solidtime by matching time and duration
            worklog_exists = False
            for solidtime_entry in issue_solidtime_entries:
                solidtime_duration = (
                    solidtime_entry.get("duration", 0) // 60
                )  # Convert to minutes
                solidtime_start = solidtime_entry.get("start", "")[
                    :10
                ]  # Extract YYYY-MM-DD part

                # Match by date and duration (with small tolerance for rounding)
                if (
                    solidtime_start == tempo_started
                    and abs(solidtime_duration - tempo_duration) <= 1
                ):  # 1 minute tolerance
                    worklog_exists = True
                    break

            if not worklog_exists:
                missing_worklogs.append(tempo_worklog)
                logger.debug(
                    f"Found missing worklog: {tempo_started} ({tempo_duration}min)"
                )

        logger.info(f"Found {len(missing_worklogs)} missing worklogs for {issue_key}")
        return missing_worklogs

    def sync_tempo_to_mapping(self, tempo_worklogs: List[Dict]) -> Dict:
        """
        Teil A: Synchronize Tempo worklogs to mapping file.

        Returns:
            Statistics about the mapping synchronization
        """
        stats = {
            "new_mappings": 0,
            "marked_for_update": 0,
            "orphaned_mappings_removed": 0,
            "unchanged_mappings": 0,
        }

        # Get all tempo worklog IDs from current fetch
        tempo_worklog_ids = {
            str(w.get("tempoWorklogId", ""))
            for w in tempo_worklogs
            if w.get("tempoWorklogId")
        }

        # Step 1: Process each Tempo worklog
        for worklog in tempo_worklogs:
            tempo_id = str(worklog.get("tempoWorklogId", ""))
            if not tempo_id:
                continue

            tempo_updated_at = worklog.get("updatedAt", "")
            issue_key = worklog.get("issue", {}).get("key", "")

            if tempo_id in self.worklog_mapping.mappings:
                # Existing mapping - check if Tempo worklog is newer
                if self.worklog_mapping.is_tempo_worklog_newer(
                    tempo_id, tempo_updated_at
                ):
                    # Update the mapping timestamp and mark for update
                    self.worklog_mapping.mappings[tempo_id]["tempo_updated_at"] = (
                        tempo_updated_at
                    )
                    self.worklog_mapping.mark_for_update(tempo_id)
                    stats["marked_for_update"] += 1
                    logger.info(
                        f"Tempo worklog {tempo_id} updated, marked for sync to Solidtime"
                    )
                else:
                    stats["unchanged_mappings"] += 1
            else:
                # New worklog - create mapping (without solidtime_entry_id yet)
                self.worklog_mapping.add_mapping(
                    tempo_id, "", issue_key, tempo_updated_at, None, needs_update=True
                )
                stats["new_mappings"] += 1
                logger.info(f"New Tempo worklog {tempo_id}, created mapping")

        # Step 2: Clean up orphaned mappings
        orphaned_mappings = []
        for tempo_id in list(self.worklog_mapping.mappings.keys()):
            if tempo_id not in tempo_worklog_ids:
                orphaned_mappings.append(tempo_id)

        for tempo_id in orphaned_mappings:
            self.worklog_mapping.remove_mapping(tempo_id)
            stats["orphaned_mappings_removed"] += 1
            logger.info(
                f"Removed orphaned mapping for deleted Tempo worklog {tempo_id}"
            )

        # Save the updated mappings
        if (
            stats["new_mappings"] > 0
            or stats["marked_for_update"] > 0
            or stats["orphaned_mappings_removed"] > 0
        ):
            self.worklog_mapping.save_mappings()

        logger.info(
            f"Tempo→Mapping sync: {stats['new_mappings']} new, {stats['marked_for_update']} updates, "
            f"{stats['orphaned_mappings_removed']} removed, {stats['unchanged_mappings']} unchanged"
        )

        return stats

    def detailed_worklog_sync_plan(
        self, tempo_worklogs: List[Dict], solidtime_entries: List[Dict]
    ) -> Tuple[List[Dict], List[Dict], List[str], List[str], Dict]:
        """
        Generate a detailed sync plan with two-stage synchronization.

        Returns:
            - List of Tempo worklogs to create
            - List of Tempo worklogs to update
            - List of Solidtime entry IDs to delete (orphaned)
            - List of Solidtime entry IDs to update
            - Detailed sync plan statistics
        """
        # Teil A: Sync Tempo → Mapping
        self.sync_tempo_to_mapping(tempo_worklogs)

        # Try to recover mappings from entry descriptions only if there are NO mappings at all
        if len(self.worklog_mapping.mappings) == 0 and len(tempo_worklogs) > 0:
            logger.info(
                "No mappings found, attempting recovery from entry descriptions..."
            )
            recovered = self.worklog_mapping.recover_mappings_from_descriptions(
                solidtime_entries
            )
            if recovered > 0:
                logger.info(f"Successfully recovered {recovered} mappings")

        # Teil B: Sync Mapping → Solidtime
        worklogs_to_create = []
        worklogs_to_update = []
        entry_ids_to_delete = []
        entry_ids_to_update = []

        # Create a lookup dict for Tempo worklogs by ID
        tempo_worklog_lookup = {
            str(w.get("tempoWorklogId", "")): w
            for w in tempo_worklogs
            if w.get("tempoWorklogId")
        }

        # ID-based synchronization - use mapping as source of truth
        # Get all Solidtime entry IDs that actually exist in the API response
        existing_solidtime_entry_ids = {
            e.get("id") for e in solidtime_entries if e.get("id")
        }

        # Create lookup dict for existing Solidtime entries by ID
        solidtime_entry_lookup = {
            e.get("id"): e for e in solidtime_entries if e.get("id")
        }

        # Get all mapped Solidtime entry IDs
        mapped_entry_ids = self.worklog_mapping.get_mapped_solidtime_entry_ids()

        # Find orphaned Solidtime entries (with [JiraSync] but no mapping) - only for cleanup
        orphaned_entries = []
        for entry in solidtime_entries:
            entry_id = entry.get("id")
            description = entry.get("description", "")
            if (
                entry_id
                and "[JiraSync" in description
                and entry_id not in mapped_entry_ids
            ):
                orphaned_entries.append(entry_id)
                logger.info(
                    f"Found orphaned Solidtime entry {entry_id} (has [JiraSync] but no mapping)"
                )

        # Add orphaned entries to deletion list
        entry_ids_to_delete.extend(orphaned_entries)

        # Process mappings to determine what needs to be done in Solidtime
        for tempo_id, mapping in self.worklog_mapping.mappings.items():
            solidtime_entry_id = mapping.get("solidtime_entry_id", "")
            needs_update = mapping.get("needs_update", False)
            # Also update if solidtime_updated_at is null (legacy entries)
            if mapping.get("solidtime_updated_at") is None:
                logger.info(
                    f"LEGACY NULL UPDATE: Entry {tempo_id} has null solidtime_updated_at"
                )
                needs_update = True

            # Find the corresponding Tempo worklog
            tempo_worklog = tempo_worklog_lookup.get(tempo_id)
            if not tempo_worklog:
                continue  # This should not happen after mapping cleanup

            if not solidtime_entry_id:
                # No Solidtime entry yet - needs creation
                worklogs_to_create.append(tempo_worklog)
                logger.info(f"Tempo worklog {tempo_id} needs creation in Solidtime")
            elif solidtime_entry_id not in existing_solidtime_entry_ids:
                # Solidtime entry was manually deleted - needs recreation
                worklogs_to_create.append(tempo_worklog)
                logger.info(
                    f"Solidtime entry {solidtime_entry_id} for Tempo worklog {tempo_id} was deleted, needs recreation"
                )
            elif needs_update:
                # Tempo worklog was updated - needs update in Solidtime
                worklogs_to_update.append(tempo_worklog)
                entry_ids_to_update.append(solidtime_entry_id)
                logger.info(
                    f"Tempo worklog {tempo_id} needs update in Solidtime entry {solidtime_entry_id}"
                )
            else:
                # Entry exists and mapping is current - check if Solidtime data differs from Tempo (SSoT)
                solidtime_entry = solidtime_entry_lookup.get(solidtime_entry_id)
                if solidtime_entry and self._solidtime_differs_from_tempo(
                    tempo_worklog, solidtime_entry
                ):
                    # Solidtime data differs from Tempo (SSoT) - needs update to restore Tempo as master
                    worklogs_to_update.append(tempo_worklog)
                    entry_ids_to_update.append(solidtime_entry_id)
                    logger.info(
                        f"SOLIDTIME DIFFERS FROM TEMPO: Entry {solidtime_entry_id} for worklog {tempo_id} differs from Tempo (SSoT), needs update"
                    )
                else:
                    logger.info(
                        f"NO DIFFERENCE DETECTED: Entry {solidtime_entry_id} for worklog {tempo_id} matches Tempo"
                    )
            # else: mapping exists and is current, no action needed

        # Generate statistics
        plan = {
            "total_tempo_worklogs": len(tempo_worklogs),
            "total_solidtime_entries": len(solidtime_entries),
            "worklogs_to_create": len(worklogs_to_create),
            "worklogs_to_update": len(worklogs_to_update),
            "entries_to_delete": len(entry_ids_to_delete),
            "entries_to_update": len(entry_ids_to_update),
            "unchanged_worklogs": len(tempo_worklogs)
            - len(worklogs_to_create)
            - len(worklogs_to_update),
        }

        logger.info(
            f"Detailed sync plan: {plan['worklogs_to_create']} new, {plan['worklogs_to_update']} updates, "
            f"{plan['entries_to_delete']} deletions, {plan['unchanged_worklogs']} unchanged"
        )

        return (
            worklogs_to_create,
            worklogs_to_update,
            entry_ids_to_delete,
            entry_ids_to_update,
            plan,
        )

    def _generate_expected_description(self, tempo_worklog: Dict) -> str:
        """Generate expected description for a Tempo worklog (same logic as field_mapper)."""
        try:
            # Extract basic info from tempo worklog - EXACT same as FieldMapper
            tempo_id = tempo_worklog.get("tempoWorklogId", "")
            worklog_description = tempo_worklog.get("description", "").strip()
            issue_key = tempo_worklog.get("issue", {}).get("key", "")
            issue_summary = tempo_worklog.get("issue", {}).get(
                "summary", "No description"
            )

            # EXACT same logic as FieldMapper.map_single_worklog()
            # Check if it's the default Tempo text "Working on issue AS-1"
            if (
                worklog_description.startswith("Working on issue")
                and issue_key in worklog_description
            ):
                # Replace with issue summary for more meaningful description
                return f"{issue_key}: {issue_summary} [JiraSync:{tempo_id}]"
            elif worklog_description:
                # Use custom worklog description
                return f"{issue_key}: {worklog_description} [JiraSync:{tempo_id}]"
            else:
                # Fallback to issue summary
                return f"{issue_key}: {issue_summary} [JiraSync:{tempo_id}]"
        except Exception as e:
            logger.debug(f"Error generating expected description: {e}")
            return ""

    def _solidtime_differs_from_tempo(
        self, tempo_worklog: Dict, solidtime_entry: Dict
    ) -> bool:
        """Check if Solidtime entry differs from Tempo worklog (SSoT) in any significant way."""
        try:
            # Compare duration (seconds)
            tempo_duration = tempo_worklog.get("timeSpentSeconds", 0)
            solidtime_start = solidtime_entry.get("start", "")
            solidtime_end = solidtime_entry.get("end", "")

            if solidtime_start and solidtime_end:
                from datetime import datetime

                try:
                    start_time = datetime.fromisoformat(
                        solidtime_start.replace("Z", "+00:00")
                    )
                    end_time = datetime.fromisoformat(
                        solidtime_end.replace("Z", "+00:00")
                    )
                    solidtime_duration = int((end_time - start_time).total_seconds())

                    if (
                        abs(tempo_duration - solidtime_duration) > 60
                    ):  # Allow 1 minute tolerance
                        logger.info(
                            f"DURATION DIFFERS: Tempo {tempo_duration}s vs Solidtime {solidtime_duration}s"
                        )
                        return True
                except Exception as e:
                    logger.debug(f"Error comparing durations: {e}")
                    return True

            # Compare date
            tempo_date = tempo_worklog.get("startDate", "")
            if solidtime_start and tempo_date:
                try:
                    tempo_date_obj = datetime.fromisoformat(tempo_date).date()
                    solidtime_date_obj = datetime.fromisoformat(
                        solidtime_start.replace("Z", "+00:00")
                    ).date()

                    if tempo_date_obj != solidtime_date_obj:
                        logger.debug(
                            f"Date differs: Tempo {tempo_date} vs Solidtime {solidtime_start}"
                        )
                        return True
                except Exception as e:
                    logger.debug(f"Error comparing dates: {e}")
                    return True

            # Compare start time (within same date)
            tempo_start_time = tempo_worklog.get("startTime", "")
            if solidtime_start and tempo_start_time:
                try:
                    # Parse tempo time (format: "HH:MM:SS")
                    tempo_hour, tempo_min, tempo_sec = map(
                        int, tempo_start_time.split(":")
                    )

                    # Parse solidtime time
                    solidtime_time = datetime.fromisoformat(
                        solidtime_start.replace("Z", "+00:00")
                    )

                    # Allow 2 minute tolerance for start time
                    tempo_total_minutes = tempo_hour * 60 + tempo_min
                    solidtime_total_minutes = (
                        solidtime_time.hour * 60 + solidtime_time.minute
                    )

                    if abs(tempo_total_minutes - solidtime_total_minutes) > 2:
                        logger.info(
                            f"START TIME DIFFERS: Tempo {tempo_start_time} ({tempo_total_minutes} min) vs Solidtime {solidtime_time.time()} ({solidtime_total_minutes} min)"
                        )
                        return True
                except Exception as e:
                    logger.debug(f"Error comparing start times: {e}")
                    return True

            # Compare descriptions - need to format Tempo description like Field Mapper does
            tempo_raw_description = tempo_worklog.get("description", "")
            issue_key = tempo_worklog.get("issue", {}).get("key", "")
            tempo_worklog_id = tempo_worklog.get("tempoWorklogId", "")

            # Format Tempo description the same way Field Mapper does
            if tempo_raw_description:
                tempo_formatted_desc = f"{issue_key}: {tempo_raw_description} [JiraSync:{tempo_worklog_id}]"
            else:
                # Fallback - just use issue key (matching field mapper fallback logic)
                issue_summary = tempo_worklog.get("issue", {}).get("summary", "")
                tempo_formatted_desc = (
                    f"{issue_key}: {issue_summary} [JiraSync:{tempo_worklog_id}]"
                )

            solidtime_description = solidtime_entry.get("description", "")

            if tempo_formatted_desc != solidtime_description:
                logger.info(
                    f"DESCRIPTION DIFFERS: Tempo '{tempo_formatted_desc}' vs Solidtime '{solidtime_description}'"
                )
                return True

            return False

        except Exception as e:
            logger.debug(f"Error in _solidtime_differs_from_tempo: {e}")
            return False  # If we can't compare, assume no difference

    def add_worklog_mapping(
        self,
        tempo_worklog: Dict,
        solidtime_entry_id: str,
        solidtime_updated_at: Optional[str] = None,
    ) -> None:
        """Add or update a mapping after successful sync."""
        tempo_id = str(tempo_worklog.get("tempoWorklogId", ""))
        issue_key = tempo_worklog.get("issue", {}).get("key", "")
        tempo_updated_at = tempo_worklog.get("updatedAt", "")

        if tempo_id and issue_key:
            if tempo_id in self.worklog_mapping.mappings:
                # Update existing mapping
                self.worklog_mapping.mappings[tempo_id]["solidtime_entry_id"] = (
                    solidtime_entry_id
                )
                self.worklog_mapping.mappings[tempo_id]["solidtime_updated_at"] = (
                    solidtime_updated_at
                )
                self.worklog_mapping.clear_update_flag(tempo_id)
            else:
                # Create new mapping
                self.worklog_mapping.add_mapping(
                    tempo_id,
                    solidtime_entry_id,
                    issue_key,
                    tempo_updated_at,
                    solidtime_updated_at,
                    needs_update=False,
                )
            self.worklog_mapping.save_mappings()

    def remove_worklog_mapping(self, tempo_worklog_id: str) -> None:
        """Remove a mapping after deletion."""
        self.worklog_mapping.remove_mapping(tempo_worklog_id)
        self.worklog_mapping.save_mappings()
