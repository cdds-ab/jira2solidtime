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
        url = f"{self.base_url}/rest/api/2{endpoint}"
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

    def get_issue(self, issue_key: str, fields: list[str] | None = None) -> dict[str, Any]:
        """Get issue details.

        Args:
            issue_key: Issue key or ID (e.g., 'PROJ-123' or '10386')
            fields: Specific fields to fetch (e.g., ['summary', 'parent'])

        Returns:
            Issue data
        """
        params = {}
        if fields:
            params["fields"] = ",".join(fields)

        response = self._make_request("GET", f"/issue/{issue_key}", params=params)
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

    def get_issues_by_ids(
        self, issue_ids: list[str], fields: list[str] | None = None
    ) -> dict[str, dict[str, Any]]:
        """Batch fetch multiple issues by IDs using JQL.

        Args:
            issue_ids: List of issue IDs (e.g., ['10386', '10387'])
            fields: Specific fields to fetch (e.g., ['summary', 'parent'])

        Returns:
            Dictionary mapping issue ID to issue data
        """
        if not issue_ids:
            return {}

        # Build JQL: id IN (10386, 10387, ...)
        ids_str = ",".join(issue_ids)
        jql = f"id IN ({ids_str})"

        params: dict[str, Any] = {"jql": jql, "maxResults": 1000}
        if fields:
            params["fields"] = ",".join(fields)

        try:
            response = self._make_request("GET", "/search", params=params)
            data = response.json()
            issues = data.get("issues", [])

            # Build dict: issue_id -> issue data
            result = {}
            for issue in issues:
                issue_id = str(issue.get("id"))
                result[issue_id] = issue

            logger.debug(f"Batch fetched {len(result)} issues from {len(issue_ids)} requested")
            return result

        except Exception as e:
            logger.error(f"Batch fetch failed: {e}")
            return {}

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
