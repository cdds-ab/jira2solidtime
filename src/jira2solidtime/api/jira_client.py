"""Minimal Jira API client for issue retrieval."""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class JiraClient:
    """Simple Jira API client."""

    def __init__(self, base_url: str, email: str, api_token: str) -> None:
        """Initialize Jira client.

        Args:
            base_url: Jira base URL
            email: User email for authentication
            api_token: Jira API token
        """
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.headers = {"Content-Type": "application/json"}

    def _make_request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
        """Make authenticated request to Jira API.

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request arguments

        Returns:
            Response object
        """
        url = f"{self.base_url}/rest/api/3{endpoint}"
        auth = (self.email, self.api_token)

        try:
            response = requests.request(
                method, url, headers=self.headers, auth=auth, timeout=30, **kwargs
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Jira API request failed: {e}")
            raise

    def get_issue(self, issue_key: str) -> dict[str, Any]:
        """Get issue details.

        Args:
            issue_key: Issue key (e.g., 'PROJ-123')

        Returns:
            Issue data
        """
        response = self._make_request("GET", f"/issues/{issue_key}")
        return response.json()

    def get_issues(self, project_key: str) -> list[dict[str, Any]]:
        """Get all issues in a project.

        Args:
            project_key: Project key

        Returns:
            List of issues
        """
        jql = f"project = {project_key} ORDER BY updated DESC"
        response = self._make_request("GET", "/search", params={"jql": jql, "maxResults": 100})
        data = response.json()
        return data.get("issues", [])

    def test_connection(self) -> bool:
        """Test if API connection works.

        Returns:
            True if connection is successful
        """
        try:
            response = self._make_request("GET", "/myself")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Jira connection test failed: {e}")
            return False
