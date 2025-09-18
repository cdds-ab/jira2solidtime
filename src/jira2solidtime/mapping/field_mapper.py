from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class FieldMapper:
    def __init__(self, mapping_rules: dict):
        self.mapping_rules = mapping_rules
        self.project_mappings = mapping_rules.get("project_mappings", {})
        self.task_mappings = mapping_rules.get("task_mappings", {})
        self.field_mappings = mapping_rules.get("field_mappings", {})

    def map_tempo_worklog(self, tempo_worklog: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map a Tempo worklog to Solidtime format.

        Args:
            tempo_worklog: Raw worklog from Tempo API

        Returns:
            Mapped worklog dictionary ready for Solidtime or CSV export
        """
        try:
            # Extract basic fields
            date = tempo_worklog.get("startDate", "")
            start_time = tempo_worklog.get(
                "startTime", "09:00"
            )  # Default if not provided
            duration_seconds = tempo_worklog.get("timeSpentSeconds", 0)
            duration_hours = round(duration_seconds / 3600, 2)

            # Extract project and issue info
            issue_info = tempo_worklog.get("issue", {})
            project_key = issue_info.get("projectKey", "")
            issue_key = issue_info.get("key", "")
            issue_type = issue_info.get("issueType", {}).get("name", "")

            # Map project
            mapped_project = self.map_project(project_key)

            # Map task based on issue type and other criteria
            mapped_task = self.map_task(issue_info)

            # Handle billable status
            billable = self.map_billable_status(tempo_worklog, project_key)

            # Build Solidtime description with JiraSync marker
            worklog_description = tempo_worklog.get("description", "").strip()
            issue_summary = issue_info.get("summary", "No description")

            # Check if it's the default Tempo text "Working on issue AS-1"
            if (
                worklog_description.startswith("Working on issue")
                and issue_key in worklog_description
            ):
                # Replace with issue summary for more meaningful description
                description = f"{issue_key}: {issue_summary} [JiraSync:{tempo_worklog.get('tempoWorklogId', '')}]"
            elif worklog_description:
                # Use custom worklog description
                description = f"{issue_key}: {worklog_description} [JiraSync:{tempo_worklog.get('tempoWorklogId', '')}]"
            else:
                # Fallback to issue summary
                description = f"{issue_key}: {issue_summary} [JiraSync:{tempo_worklog.get('tempoWorklogId', '')}]"

            mapped_worklog = {
                "date": date,
                "start_time": start_time,
                "duration_hours": duration_hours,
                "project": mapped_project,
                "task": mapped_task,
                "description": description,
                "billable": billable,
                "jira_issue_key": issue_key,
                # Keep original data for reference
                "tempo_worklog_id": tempo_worklog.get("tempoWorklogId"),
                "jira_worklog_id": tempo_worklog.get("jiraWorklogId"),
                "project_key": project_key,
                "issue_type": issue_type,
            }

            logger.debug(
                f"Mapped worklog: {issue_key} -> {mapped_project}/{mapped_task}"
            )
            return mapped_worklog

        except Exception as e:
            logger.error(
                f"Error mapping worklog {tempo_worklog.get('tempoWorklogId', 'unknown')}: {e}"
            )
            raise

    def map_project(self, project_key: str) -> str:
        """Map Jira project key to Solidtime project name."""
        mapped = self.project_mappings.get(project_key, project_key)

        # Only log warning if project_mappings is not empty but key is missing
        if (
            mapped == project_key
            and project_key not in self.project_mappings
            and self.project_mappings
        ):  # Only warn if mappings exist but key is missing
            logger.debug(f"Using default mapping for project '{project_key}'")

        return str(mapped)

    def map_task(self, issue_info: Dict[str, Any]) -> str:
        """Map issue information to Solidtime task name."""
        issue_type = issue_info.get("issueType", {}).get("name", "")
        labels = issue_info.get("labels", [])

        # First check label-based mappings
        label_mappings = self.task_mappings.get("labels", {})
        for label in labels:
            if label.lower() in label_mappings:
                return str(label_mappings[label.lower()])

        # Then check issue type mappings
        issue_type_mappings = self.task_mappings.get("issue_types", {})
        if issue_type in issue_type_mappings:
            return str(issue_type_mappings[issue_type])

        # Fallback to default
        default_task = self.task_mappings.get("default", "General Work")
        logger.debug(
            f"Using default task '{default_task}' for issue type '{issue_type}'"
        )
        return str(default_task)

    def map_billable_status(
        self, tempo_worklog: Dict[str, Any], project_key: str
    ) -> bool:
        """Determine billable status based on worklog and project."""
        billable_rules = self.field_mappings.get("billable_rules", {})
        default_rule = billable_rules.get("default", "auto")
        overrides = billable_rules.get("overrides", {})

        # Check project-specific overrides first
        if project_key in overrides:
            override_rule = overrides[project_key]
            if override_rule == "always_billable":
                return True
            elif override_rule == "never_billable":
                return False

        # Apply default rule
        if default_rule == "always_billable":
            return True
        elif default_rule == "never_billable":
            return False
        else:  # 'auto'
            # Check if Tempo has billable seconds > 0
            billable_seconds = tempo_worklog.get("billableSeconds", 0)
            return bool(billable_seconds > 0)

    def map_multiple_worklogs(
        self, tempo_worklogs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Map multiple Tempo worklogs to Solidtime format."""
        mapped_worklogs = []

        for worklog in tempo_worklogs:
            try:
                mapped = self.map_tempo_worklog(worklog)
                mapped_worklogs.append(mapped)
            except Exception as e:
                logger.error(f"Skipping worklog due to mapping error: {e}")
                continue

        logger.info(
            f"Successfully mapped {len(mapped_worklogs)}/{len(tempo_worklogs)} worklogs"
        )
        return mapped_worklogs

    def get_mapping_stats(
        self, mapped_worklogs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate statistics about the mapping results."""
        stats: Dict[str, Any] = {
            "total_worklogs": len(mapped_worklogs),
            "projects": {},
            "tasks": {},
            "billable_hours": 0,
            "non_billable_hours": 0,
        }

        for worklog in mapped_worklogs:
            project = worklog.get("project", "Unknown")
            task = worklog.get("task", "Unknown")
            duration = worklog.get("duration_hours", 0)
            billable = worklog.get("billable", False)

            # Count projects and tasks
            stats["projects"][project] = stats["projects"].get(project, 0) + 1
            stats["tasks"][task] = stats["tasks"].get(task, 0) + 1

            # Sum billable/non-billable hours
            if billable:
                stats["billable_hours"] += duration
            else:
                stats["non_billable_hours"] += duration

        return stats
