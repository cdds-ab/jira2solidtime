"""Minimal Solidtime API client for time entry management."""

import logging
from datetime import datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)


class SolidtimeClient:
    """Simple Solidtime API client."""

    def __init__(self, base_url: str, api_token: str, organization_id: str) -> None:
        """Initialize Solidtime client.

        Args:
            base_url: Solidtime base URL
            api_token: API token for authentication
            organization_id: Organization ID
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.organization_id = organization_id
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    def _make_request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
        """Make authenticated request to Solidtime API.

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request arguments

        Returns:
            Response object
        """
        url = f"{self.base_url}/api/v1{endpoint}"

        try:
            response = requests.request(method, url, headers=self.headers, timeout=30, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Solidtime API request failed: {e}")
            raise

    def get_projects(self) -> list[dict[str, Any]]:
        """Get all projects in organization.

        Returns:
            List of projects
        """
        endpoint = f"/organizations/{self.organization_id}/projects"
        response = self._make_request("GET", endpoint)
        data = response.json()
        return data.get("data", [])

    def create_time_entry(
        self,
        project_id: str,
        task_id: str,
        duration_minutes: int,
        date: datetime,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a time entry.

        Args:
            project_id: Solidtime project ID
            task_id: Solidtime task ID
            duration_minutes: Duration in minutes
            date: Entry date
            description: Entry description

        Returns:
            Created time entry data
        """
        payload = {
            "project_id": project_id,
            "task_id": task_id,
            "duration": duration_minutes,
            "date": date.isoformat(),
            "description": description,
        }

        endpoint = f"/organizations/{self.organization_id}/time-entries"
        response = self._make_request("POST", endpoint, json=payload)
        return response.json()

    def get_time_entries(self, start_date: datetime, end_date: datetime) -> list[dict[str, Any]]:
        """Get time entries for date range.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of time entries
        """
        params = {
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
        }
        endpoint = f"/organizations/{self.organization_id}/time-entries"
        response = self._make_request("GET", endpoint, params=params)
        data = response.json()
        return data.get("data", [])

    def test_connection(self) -> bool:
        """Test if API connection works.

        Returns:
            True if connection is successful
        """
        try:
            response = self._make_request("GET", "/users/me")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Solidtime connection test failed: {e}")
            return False
