"""Minimal Solidtime API client for time entry management."""

import logging
from datetime import datetime, timedelta
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
        self._member_id: str | None = None

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
            # Log detailed error info for debugging
            try:
                error_data = response.json()
                logger.error(f"Solidtime API request failed: {e}")
                logger.error(f"  Response: {error_data}")
            except Exception:
                logger.error(f"Solidtime API request failed: {e}")
                logger.error(f"  Response: {response.text}")
            raise

    def get_user_memberships(self) -> list[dict[str, Any]]:
        """Get current user's memberships across organizations.

        Uses fallback strategy to handle different API versions.

        Returns:
            List of membership objects

        Raises:
            RequestException: If all API calls fail
        """
        # Try multiple endpoints with fallback strategy
        endpoints = [
            "/users/me/memberships",
            "/users/memberships",
            "/memberships",
        ]

        for endpoint in endpoints:
            try:
                response = self._make_request("GET", endpoint)
                data = response.json()
                memberships = data.get("data", [])
                if memberships:
                    logger.debug(f"Got memberships from {endpoint}: {len(memberships)} found")
                    return memberships
            except Exception as e:
                logger.debug(f"Endpoint {endpoint} failed: {e}, trying next...")
                continue

        raise ValueError("Could not get memberships from any endpoint")

    def _get_member_id(self) -> str:
        """Get current user's member ID for the organization (cached).

        Gets the membership ID for the current organization, not the user ID.

        Returns:
            Member ID (organization-specific membership ID)

        Raises:
            ValueError: If membership not found for organization
        """
        if self._member_id:
            return self._member_id

        # Get all memberships and find the one for our organization
        memberships = self.get_user_memberships()

        for membership in memberships:
            org_id = membership.get("organization", {}).get("id")
            if org_id == self.organization_id:
                member_id = membership.get("id")
                if member_id:
                    self._member_id = str(member_id)
                    logger.debug(
                        f"Found member_id {self._member_id} for org {self.organization_id}"
                    )
                    return self._member_id

        raise ValueError(f"Could not find membership for organization {self.organization_id}")

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
        duration_minutes: int,
        date: datetime,
        description: str = "",
        billable: bool = True,
    ) -> dict[str, Any]:
        """Create a time entry.

        Args:
            project_id: Solidtime project ID
            duration_minutes: Duration in minutes
            date: Entry date and time
            description: Entry description
            billable: Whether time entry is billable

        Returns:
            Created time entry data
        """
        # Get current user's member ID for this organization
        member_id = self._get_member_id()

        # Convert minutes to seconds
        duration_seconds = duration_minutes * 60

        # Format start time with Z suffix (UTC timezone)
        # Expected format: 2025-10-23T08:00:00Z
        start_str = date.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Calculate end time = start + duration
        end_date = date + timedelta(seconds=duration_seconds)
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        payload = {
            "member_id": member_id,
            "project_id": project_id,
            "start": start_str,
            "end": end_str,
            "duration": duration_seconds,
            "billable": billable,
            "description": description,
        }

        logger.debug(f"Creating time entry: {payload}")

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
