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
        """Batch fetch multiple issues by IDs using enhanced JQL search.

        Tries new enhanced search API first, falls back to legacy v2 if unavailable.

        Args:
            issue_ids: List of issue IDs (e.g., ['10386', '10387'])
            fields: Specific fields to fetch (e.g., ['summary', 'parent'])

        Returns:
            Dictionary mapping issue ID to issue data
        """
        if not issue_ids:
            return {}

        ids_str = ",".join(issue_ids)
        jql = f"id IN ({ids_str})"

        # Try enhanced search API first (v3/search/jql)
        try:
            return self._fetch_with_enhanced_search(jql, fields, len(issue_ids))
        except requests.RequestException as e:
            # Fallback to legacy API on 404/410 (older Jira instances)
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                if status_code in [404, 410]:
                    logger.warning(
                        f"Enhanced search unavailable ({status_code}), falling back to legacy API"
                    )
                    try:
                        return self._fetch_with_legacy_search(jql, fields, len(issue_ids))
                    except Exception as legacy_error:
                        logger.error(f"Legacy search also failed: {legacy_error}")
                        return {}
            logger.error(f"Batch fetch failed: {e}")
            return {}

    def _fetch_with_enhanced_search(
        self, jql: str, fields: list[str] | None, max_results: int
    ) -> dict[str, dict[str, Any]]:
        """Use new enhanced search API: POST /rest/api/3/search/jql.

        Args:
            jql: JQL query string
            fields: Fields to fetch
            max_results: Maximum number of results

        Returns:
            Dictionary mapping issue ID to issue data
        """
        url = f"{self.base_url}/rest/api/3/search/jql"
        auth = (self.email, self.api_token)

        payload: dict[str, Any] = {
            "jql": jql,
            "maxResults": min(max_results, 1000),
            "fieldsByKeys": False,
        }

        if fields:
            payload["fields"] = fields

        response = requests.post(url, json=payload, headers=self.headers, auth=auth, timeout=30)
        response.raise_for_status()

        data = response.json()
        issues = data.get("issues", [])

        # Build dict: issue_id -> issue data
        result = {}
        for issue in issues:
            issue_id = str(issue.get("id"))
            result[issue_id] = issue

        logger.debug(f"Enhanced search fetched {len(result)} issues")
        return result

    def _fetch_with_legacy_search(
        self, jql: str, fields: list[str] | None, max_results: int
    ) -> dict[str, dict[str, Any]]:
        """Fallback to legacy search: GET /rest/api/2/search.

        Args:
            jql: JQL query string
            fields: Fields to fetch
            max_results: Maximum number of results

        Returns:
            Dictionary mapping issue ID to issue data
        """
        params: dict[str, Any] = {"jql": jql, "maxResults": min(max_results, 1000)}
        if fields:
            params["fields"] = ",".join(fields)

        response = self._make_request("GET", "/search", params=params)
        data = response.json()
        issues = data.get("issues", [])

        result = {}
        for issue in issues:
            issue_id = str(issue.get("id"))
            result[issue_id] = issue

        logger.debug(f"Legacy search fetched {len(result)} issues")
        return result

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
