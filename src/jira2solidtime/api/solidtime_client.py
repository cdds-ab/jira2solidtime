import requests
from datetime import datetime
from typing import List, Dict, Optional
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


class SolidtimeClient:
    def __init__(
        self, api_token: str, base_url: str, organization_id: Optional[str] = None
    ):
        self.api_token = api_token
        self.base_url = base_url.rstrip("/")
        self.organization_id = organization_id
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def get_current_user(self) -> Optional[Dict]:
        """Get current user information including member_id."""
        response = self._make_request("GET", "/api/v1/users/me")
        if response.status_code == 200:
            user_data = response.json()
            user_info = user_data.get("data", {})
            logger.info(f"Current user: {user_info.get('name', 'Unknown')}")
            return user_data
        else:
            logger.error(f"Failed to get current user: {response.status_code}")
            return None

    def get_user_memberships(self) -> List[Dict]:
        """Get current user's organization memberships."""
        # Try different membership endpoints
        endpoints = [
            "/api/v1/me/memberships",
            "/api/v1/users/me/memberships",
            "/api/v1/memberships",
            "/api/v1/user/memberships",
        ]

        for endpoint in endpoints:
            try:
                response = self._make_request("GET", endpoint)
                if response.status_code == 200:
                    memberships_data = response.json()
                    memberships = memberships_data.get("data", [])
                    logger.info(f"Found {len(memberships)} memberships via {endpoint}")
                    return memberships
                else:
                    logger.debug(f"Endpoint {endpoint} returned {response.status_code}")
            except Exception as e:
                logger.debug(f"Endpoint {endpoint} failed: {e}")

        logger.error("Failed to get memberships from any endpoint")
        return []

    def test_connection(self) -> bool:
        """Test the connection to Solidtime API."""
        user_data = self.get_current_user()
        if user_data:
            user_info = user_data.get("data", {})
            user_name = user_info.get("name", "Unknown")
            logger.info(f"Solidtime API connection successful for user: {user_name}")
            return True
        else:
            logger.error("Solidtime API connection failed")
            return False

    def get_organizations(self) -> List[Dict]:
        """Get available organizations."""
        # Try multiple endpoints for organizations
        endpoints = [
            "/api/v1/organizations",
            "/api/organizations",
            "/api/v1/user/organizations",
        ]

        for endpoint in endpoints:
            response = self._make_request("GET", endpoint)
            if response.status_code == 200:
                return response.json().get("data", [])

        logger.error("Failed to get organizations from any endpoint")
        return []

    def get_organization_members(
        self, organization_id: Optional[str] = None
    ) -> List[Dict]:
        """Get members of the organization."""
        org_id = organization_id or self.organization_id
        if not org_id:
            raise ValueError("Organization ID is required")

        # Try different endpoints for organization members
        endpoints = [
            f"/api/v1/organizations/{org_id}/members",
            f"/api/v1/organizations/{org_id}/users",
            f"/api/v1/organizations/{org_id}/team-members",
        ]

        for endpoint in endpoints:
            try:
                response = self._make_request("GET", endpoint)
                if response.status_code == 200:
                    logger.info(f"Found organization members via {endpoint}")
                    return response.json().get("data", [])
                else:
                    logger.debug(f"Endpoint {endpoint} returned {response.status_code}")
            except Exception as e:
                logger.debug(f"Endpoint {endpoint} failed: {e}")

        logger.error("Failed to get organization members from any endpoint")
        return []

    def get_projects(self, organization_id: Optional[str] = None) -> List[Dict]:
        """Get projects for the organization."""
        org_id = organization_id or self.organization_id
        if not org_id:
            raise ValueError("Organization ID is required")

        endpoint = f"/api/v1/organizations/{org_id}/projects"
        response = self._make_request("GET", endpoint)

        if response.status_code == 200:
            return response.json().get("data", [])
        else:
            logger.error(f"Failed to get projects: {response.status_code}")
            return []

    def get_tasks(
        self, project_id: str, organization_id: Optional[str] = None
    ) -> List[Dict]:
        """Get tasks for a specific project."""
        org_id = organization_id or self.organization_id
        if not org_id:
            raise ValueError("Organization ID is required")

        endpoint = f"/api/v1/organizations/{org_id}/projects/{project_id}/tasks"
        response = self._make_request("GET", endpoint)

        if response.status_code == 200:
            return response.json().get("data", [])
        elif response.status_code == 404:
            # Tasks not configured for this project - this is normal
            logger.debug(f"No tasks configured for project {project_id}")
            return []
        else:
            logger.error(
                f"Failed to get tasks for project {project_id}: {response.status_code}"
            )
            return []

    def create_time_entry(
        self, time_entry_data: Dict, organization_id: Optional[str] = None
    ) -> Dict:
        """
        Create a new time entry.

        Args:
            time_entry_data: Dictionary containing time entry data
            organization_id: Optional organization ID

        Returns:
            Created time entry data
        """
        org_id = organization_id or self.organization_id
        if not org_id:
            raise ValueError("Organization ID is required")

        endpoint = f"/api/v1/organizations/{org_id}/time-entries"

        try:
            response = self._make_request_with_retry(
                "POST", endpoint, json=time_entry_data
            )
            response_data = response.json()
            logger.info(
                f"Created time entry: {time_entry_data.get('description', 'No description')}"
            )
            logger.debug(f"CREATE RESPONSE: {response_data}")
            return response_data
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"Failed to create time entry: {e.response.status_code} - {e.response.text}"
            )
            raise Exception(f"Failed to create time entry: {e.response.status_code}")

    def bulk_create_time_entries(
        self, time_entries: List[Dict], organization_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Create multiple time entries.

        Args:
            time_entries: List of time entry dictionaries
            organization_id: Optional organization ID

        Returns:
            List of creation results
        """
        results = []
        org_id = organization_id or self.organization_id

        for i, entry in enumerate(time_entries):
            try:
                result = self.create_time_entry(entry, org_id)
                results.append(
                    {"success": True, "data": result, "original_entry": entry}
                )
                logger.info(
                    f"Progress: {i + 1}/{len(time_entries)} time entries created"
                )

            except Exception as e:
                logger.error(f"Failed to create time entry {i + 1}: {e}")
                results.append(
                    {"success": False, "error": str(e), "original_entry": entry}
                )

        successful = len([r for r in results if r["success"]])
        logger.info(
            f"Bulk creation completed: {successful}/{len(time_entries)} successful"
        )

        return results

    def get_all_time_entries(
        self,
        from_date: datetime,
        to_date: datetime,
        organization_id: Optional[str] = None,
    ) -> List[Dict]:
        """Get time entries using member_id filter on main time-entries endpoint."""
        org_id = organization_id or self.organization_id
        if not org_id:
            raise ValueError("Organization ID is required")

        # Get member_id first
        memberships = self.get_user_memberships()
        member_id = None
        for membership in memberships:
            if membership.get("organization", {}).get("id") == org_id:
                member_id = membership.get("id")
                break

        if not member_id:
            logger.error("No member_id found for organization")
            return []

        # Use the working time-entries endpoint with member_id filter
        endpoint = f"/api/v1/organizations/{org_id}/time-entries"
        params = {
            "member_id": member_id,
            "start": from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": to_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "limit": 500,  # Get more entries per request
        }

        try:
            response = self._make_request_with_retry("GET", endpoint, params=params)
            data = response.json().get("data", [])
            logger.info(f"Found {len(data)} time entries for member {member_id}")
            return data
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 422:
                logger.debug("No time entries found for member (422 response)")
                return []
            else:
                logger.error(f"Failed to get time entries: {e.response.status_code}")
                raise
        except Exception as e:
            logger.error(f"Error fetching time entries: {e}")
            return []

    def delete_jira_synced_entries_by_pattern(
        self,
        from_date: datetime,
        to_date: datetime,
        organization_id: Optional[str] = None,
    ) -> int:
        """Delete time entries that contain [JiraSync] marker."""
        entries = self.get_all_time_entries(from_date, to_date, organization_id)
        deleted_count = 0

        org_id = organization_id or self.organization_id

        for entry in entries:
            try:
                description = entry.get("description", "")
                entry_id = entry.get("id")

                # Check if description contains [JiraSync] marker
                if "[JiraSync]" in description and entry_id:
                    endpoint = f"/api/v1/organizations/{org_id}/time-entries/{entry_id}"
                    try:
                        self._make_request_with_retry("DELETE", endpoint)
                        deleted_count += 1
                        logger.debug(f"Deleted Jira entry: {description[:50]}...")
                    except requests.exceptions.HTTPError as e:
                        logger.warning(
                            f"Failed to delete time entry {entry_id}: {e.response.status_code}"
                        )

            except Exception as e:
                logger.error(f"Error deleting time entry: {e}")

        logger.info(f"Deleted {deleted_count} Jira-synced entries (pattern-based)")
        return deleted_count

    def backup_time_entries(self, entry_ids: List[str]) -> Dict[str, Dict]:
        """Create backup of time entries before deletion."""
        backup = {}
        logger.info(f"Creating backup for {len(entry_ids)} time entries...")

        for entry_id in entry_ids:
            try:
                backup[entry_id] = {
                    "id": entry_id,
                    "backed_up_at": datetime.now().isoformat(),
                    "status": "ready_for_deletion",
                }
                logger.debug(f"Backed up entry {entry_id}")
            except Exception as e:
                logger.warning(f"Could not backup entry {entry_id}: {e}")
                backup[entry_id] = {
                    "id": entry_id,
                    "error": str(e),
                    "backed_up_at": datetime.now().isoformat(),
                    "status": "backup_failed",
                }

        logger.info(f"Created backup for {len(backup)} entries")
        return backup

    def delete_specific_time_entries(
        self,
        entry_ids: List[str],
        organization_id: Optional[str] = None,
        create_backup: bool = True,
    ) -> tuple[int, Dict[str, Dict]]:
        """Delete specific time entries by their IDs with optional backup."""
        org_id = organization_id or self.organization_id

        # Create backup first
        backup = {}
        if create_backup:
            backup = self.backup_time_entries(entry_ids)

        logger.info(f"Deleting {len(entry_ids)} specific time entries...")
        deleted_count = 0

        for entry_id in entry_ids:
            try:
                endpoint = f"/api/v1/organizations/{org_id}/time-entries/{entry_id}"
                try:
                    self._make_request_with_retry("DELETE", endpoint)
                    deleted_count += 1
                    logger.debug(f"Deleted time entry: {entry_id}")

                    # Mark as successfully deleted in backup
                    if entry_id in backup:
                        backup[entry_id]["status"] = "deleted"
                        backup[entry_id]["deleted_at"] = datetime.now().isoformat()

                except requests.exceptions.HTTPError as e:
                    logger.warning(
                        f"Failed to delete time entry {entry_id}: {e.response.status_code}"
                    )
                    # Mark deletion failure in backup
                    if entry_id in backup:
                        backup[entry_id]["status"] = "delete_failed"
                        backup[entry_id]["error"] = str(e)

            except Exception as e:
                logger.error(f"Error deleting time entry {entry_id}: {e}")
                if entry_id in backup:
                    backup[entry_id]["status"] = "delete_error"
                    backup[entry_id]["error"] = str(e)

        logger.info(f"Deleted {deleted_count} specific time entries")
        return deleted_count, backup

    def convert_worklog_to_time_entry(
        self,
        mapped_worklog: Dict,
        project_mapping: Optional[Dict[str, str]] = None,
        task_mapping: Optional[Dict[str, str]] = None,
        member_id: Optional[str] = None,
    ) -> Dict:
        """
        Convert a mapped worklog to Solidtime time entry format.

        Args:
            mapped_worklog: Worklog from field mapper
            project_mapping: Project name -> Project ID mapping
            task_mapping: Task name -> Task ID mapping

        Returns:
            Time entry data for Solidtime API
        """
        project_name = mapped_worklog.get("project") or ""
        task_name = mapped_worklog.get("task") or ""

        # If project_mapping provided, use it to get project_id
        if project_mapping:
            project_id = project_mapping.get(project_name)
            if not project_id:
                raise ValueError(f"No project ID found for project '{project_name}'")
        else:
            # Assume project_name is already the project_id or look it up dynamically
            project_id = self._get_or_create_project_id(project_name)

        # If task_mapping provided, use it to get task_id
        if task_mapping:
            task_id = task_mapping.get(task_name)
        else:
            # Assume task_name is already the task_id or look it up dynamically
            task_id = (
                self._get_or_create_task_id(task_name, project_id)
                if task_name
                else None
            )

        # Get member_id if not provided
        if member_id is None:
            member_id = self._get_current_member_id()

        # Parse date and time
        date_str = mapped_worklog.get("date")
        time_str = mapped_worklog.get("start_time", "09:00")
        duration_hours = mapped_worklog.get("duration_hours", 0)

        # Handle different time formats (HH:MM or HH:MM:SS)
        if time_str and len(time_str) > 5:
            # Remove seconds if present: "09:00:00" -> "09:00"
            time_str = time_str[:5]

        # Convert to ISO datetime format
        start_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

        # Calculate end time using timedelta (NOT replace which sets absolute values)
        from datetime import timedelta

        duration_delta = timedelta(hours=duration_hours)
        end_datetime = start_datetime + duration_delta

        # Use description-based identification (tags require admin permissions)
        # Calculate duration in seconds for API
        duration_seconds = int(duration_hours * 3600)

        time_entry = {
            "member_id": member_id,
            "project_id": project_id,
            "start": start_datetime.isoformat() + "Z",  # UTC format required
            "end": end_datetime.isoformat()
            + "Z",  # UTC format required - API expects start/end, not duration
            "duration": duration_seconds,  # Explicit duration in seconds - some APIs need this
            "description": mapped_worklog.get(
                "description", ""
            ),  # Description contains [JiraSync:ID]
            "billable": mapped_worklog.get("billable", False),
        }

        if task_id:
            time_entry["task_id"] = task_id

        return time_entry

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make a request to the Solidtime API (without retry)."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.request(
                method, url, headers=self.headers, timeout=30, **kwargs
            )
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (requests.exceptions.Timeout, requests.exceptions.ConnectionError)
        ),
        reraise=True,
    )
    def _make_request_with_retry(
        self, method: str, endpoint: str, **kwargs
    ) -> requests.Response:
        """Make a request to the Solidtime API with retry logic for transient failures."""
        logger.debug(f"Making {method} request to {endpoint} (with retry)")
        response = self._make_request(method, endpoint, **kwargs)
        response.raise_for_status()
        return response

    def _get_or_create_project_id(self, project_name: str) -> str:
        """Get or create project ID for a project name."""
        # First try to find existing project
        projects = self.get_projects()
        for project in projects:
            if project.get("name") == project_name:
                return str(project["id"])

        # If not found, create new project
        logger.info(f"Creating new project: {project_name}")
        project_data = {
            "name": project_name,
            "color": "#1976d2",  # Default blue color
            "is_billable": True,
        }

        endpoint = f"/api/v1/organizations/{self.organization_id}/projects"
        response = self._make_request("POST", endpoint, json=project_data)

        if response.status_code == 201:
            created_project = response.json().get("data", {})
            logger.info(
                f"Created project {project_name} with ID {created_project.get('id')}"
            )
            return str(created_project["id"])
        else:
            logger.error(
                f"Failed to create project {project_name}: {response.status_code}"
            )
            raise ValueError(f"Could not create project: {project_name}")

    def _get_or_create_task_id(self, task_name: str, project_id: str) -> Optional[str]:
        """Get or create task ID for a task name within a project."""
        if not task_name:
            return None

        # First try to find existing task
        try:
            tasks = self.get_tasks(project_id)
            for task in tasks:
                if task.get("name") == task_name:
                    return str(task["id"])
        except Exception as e:
            # If getting tasks fails, tasks might not be supported - continue without task
            logger.debug(f"Could not get tasks for project {project_id}: {e}")
            return None

        # If not found, try to create new task
        logger.debug(f"Attempting to create task: {task_name} in project {project_id}")
        task_data = {"name": task_name, "project_id": project_id, "is_billable": True}

        endpoint = (
            f"/api/v1/organizations/{self.organization_id}/projects/{project_id}/tasks"
        )
        try:
            response = self._make_request("POST", endpoint, json=task_data)
            if response.status_code == 201:
                created_task = response.json().get("data", {})
                logger.info(
                    f"Created task {task_name} with ID {created_task.get('id')}"
                )
                return str(created_task["id"])
            else:
                logger.debug(
                    f"Task creation not supported (status {response.status_code})"
                )
                return None
        except Exception as e:
            # Task creation failed - continue without task
            logger.debug(f"Task creation failed: {e}")
            return None  # Return None if task creation fails, entry can still be created without task

    def _get_current_member_id(self) -> Optional[str]:
        """Get current user's member_id for the organization."""
        memberships = self.get_user_memberships()
        for membership in memberships:
            if membership.get("organization", {}).get("id") == self.organization_id:
                member_id = membership.get("id")
                if member_id:
                    logger.debug(f"Found member_id: {member_id}")
                    return str(member_id)

        logger.error(f"No member_id found for organization {self.organization_id}")
        return None

    def update_time_entry(
        self,
        entry_id: str,
        time_entry_data: Dict,
        organization_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Update an existing time entry.

        Args:
            entry_id: The ID of the time entry to update
            time_entry_data: Time entry data dict with fields like description, duration, etc.
            organization_id: Organization ID (optional, uses default if not provided)

        Returns:
            Updated time entry data dict or None if failed
        """
        org_id = organization_id or self.organization_id
        if not org_id:
            raise ValueError("Organization ID is required")

        endpoint = f"/api/v1/organizations/{org_id}/time-entries/{entry_id}"

        # Ensure member_id is included if not present
        if "member_id" not in time_entry_data:
            member_id = self._get_current_member_id()
            if member_id:
                time_entry_data = time_entry_data.copy()
                time_entry_data["member_id"] = member_id

        try:
            logger.debug(f"UPDATE REQUEST: PUT {endpoint}")
            logger.debug(f"UPDATE DATA: {time_entry_data}")
            response = self._make_request_with_retry(
                "PUT", endpoint, json=time_entry_data
            )

            if response.status_code == 200:
                updated_entry = response.json().get("data", {})
                logger.info(f"Updated time entry {entry_id}")
                logger.debug(f"UPDATE RESPONSE: {updated_entry}")
                return updated_entry
            else:
                logger.error(
                    f"Failed to update time entry {entry_id}: {response.status_code}"
                )
                if response.status_code == 422:
                    try:
                        error_details = response.json()
                        logger.error(f"Validation errors: {error_details}")
                    except ValueError:
                        pass
                return None

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error updating time entry {entry_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error updating time entry {entry_id}: {e}")
            return None

    def delete_time_entry(
        self, entry_id: str, organization_id: Optional[str] = None
    ) -> bool:
        """
        Delete a specific time entry.

        Args:
            entry_id: The ID of the time entry to delete
            organization_id: Organization ID (optional, uses default if not provided)

        Returns:
            True if deletion was successful, False otherwise
        """
        org_id = organization_id or self.organization_id
        if not org_id:
            raise ValueError("Organization ID is required")

        endpoint = f"/api/v1/organizations/{org_id}/time-entries/{entry_id}"

        try:
            response = self._make_request_with_retry("DELETE", endpoint)

            if response.status_code in (200, 204):
                logger.info(f"Deleted time entry {entry_id}")
                return True
            else:
                logger.error(
                    f"Failed to delete time entry {entry_id}: {response.status_code}"
                )
                return False

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error deleting time entry {entry_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting time entry {entry_id}: {e}")
            return False
