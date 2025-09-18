import requests
import base64
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def extract_text_from_adf(adf_content) -> str:
    """Extract plain text from Atlassian Document Format (ADF)."""
    if not isinstance(adf_content, dict):
        return str(adf_content)

    text_parts = []

    def extract_text_recursive(node):
        if isinstance(node, dict):
            if node.get("type") == "text":
                text_parts.append(node.get("text", ""))
            elif "content" in node:
                for child in node["content"]:
                    extract_text_recursive(child)
        elif isinstance(node, list):
            for item in node:
                extract_text_recursive(item)

    extract_text_recursive(adf_content)
    return " ".join(text_parts).strip()


class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.api_token = api_token

        # Create Basic Auth header (email:token -> base64)
        auth_string = f"{email}:{api_token}"
        auth_bytes = auth_string.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

        self.headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def test_connection(self) -> bool:
        """Test the connection to Jira API."""
        try:
            # Test with getting current user info
            response = self._make_request("GET", "/rest/api/3/myself")
            if response.status_code == 200:
                user_data = response.json()
                logger.info(
                    f"Jira API connection successful for user: {user_data.get('displayName', 'Unknown')}"
                )
                return True
            else:
                logger.error(f"Jira API connection failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Jira API connection failed: {e}")
            return False

    def get_user_worklogs(
        self, from_date: datetime, to_date: datetime, max_results: int = 1000
    ) -> List[Dict]:
        """
        Get worklogs for the authenticated user using Jira's worklog search.

        Args:
            from_date: Start date for worklog retrieval
            to_date: End date for worklog retrieval
            max_results: Maximum number of results to return

        Returns:
            List of worklog dictionaries
        """
        # Format dates for Jira API (YYYY-MM-DD)
        from_str = from_date.strftime("%Y-%m-%d")
        to_str = to_date.strftime("%Y-%m-%d")

        # Use worklog search endpoint
        endpoint = "/rest/api/3/worklog/updated"
        params = {
            "since": int(from_date.timestamp() * 1000),  # Jira expects milliseconds
            "expand": "properties",
        }

        logger.info(f"Fetching worklogs from {from_str} to {to_str}")

        try:
            response = self._make_request("GET", endpoint, params=params)
            response.raise_for_status()

            data = response.json()
            worklog_ids = [w["worklogId"] for w in data.get("values", [])]

            if not worklog_ids:
                logger.info("No worklog IDs found")
                return []

            # Get detailed worklog information
            detailed_worklogs = []
            for worklog_id in worklog_ids:
                try:
                    worklog_detail = self.get_worklog_by_id(worklog_id)
                    if worklog_detail and self._is_worklog_in_date_range(
                        worklog_detail, from_date, to_date
                    ):
                        # Check if worklog belongs to current user
                        if (
                            worklog_detail.get("author", {}).get("emailAddress")
                            == self.email
                        ):
                            detailed_worklogs.append(worklog_detail)
                except Exception as e:
                    logger.warning(
                        f"Failed to get details for worklog {worklog_id}: {e}"
                    )
                    continue

            logger.info(f"Retrieved {len(detailed_worklogs)} worklogs for user")
            return detailed_worklogs

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching worklogs: {e}")
            raise

    def get_worklog_by_id(self, worklog_id: str) -> Optional[Dict]:
        """Get a specific worklog by ID."""
        endpoint = f"/rest/api/3/worklog/{worklog_id}"

        try:
            response = self._make_request("GET", endpoint)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    f"Failed to get worklog {worklog_id}: {response.status_code}"
                )
                return None
        except Exception as e:
            logger.error(f"Error fetching worklog {worklog_id}: {e}")
            return None

    def search_issues_with_worklogs(
        self, from_date: datetime, to_date: datetime, user_email: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for issues that have worklogs in the given date range.
        This is an alternative approach to get worklogs.
        """
        from_str = from_date.strftime("%Y-%m-%d")
        to_str = to_date.strftime("%Y-%m-%d")

        # JQL to find issues with worklogs in date range
        jql = f'worklogDate >= "{from_str}" AND worklogDate <= "{to_str}"'
        if user_email:
            jql += f' AND worklogAuthor = "{user_email}"'

        endpoint = "/rest/api/3/search"
        params = {
            "jql": jql,
            "fields": "summary,project,issuetype,worklog",
            "expand": "changelog",
            "maxResults": 1000,
        }

        try:
            response = self._make_request("GET", endpoint, params=params)
            response.raise_for_status()

            data = response.json()
            issues = data.get("issues", [])

            logger.info(f"Found {len(issues)} issues with worklogs")

            # Extract worklogs from issues
            all_worklogs = []
            for issue in issues:
                issue_key = issue.get("key")
                worklogs = (
                    issue.get("fields", {}).get("worklog", {}).get("worklogs", [])
                )

                for worklog in worklogs:
                    # Add issue context to worklog
                    worklog["issue"] = {
                        "key": issue_key,
                        "summary": issue.get("fields", {}).get("summary"),
                        "projectKey": issue.get("fields", {})
                        .get("project", {})
                        .get("key"),
                        "issueType": issue.get("fields", {}).get("issuetype", {}),
                    }

                    # Filter by date range only (include all users for debugging)
                    if self._is_worklog_in_date_range(worklog, from_date, to_date):
                        all_worklogs.append(worklog)

            logger.info(f"Extracted {len(all_worklogs)} relevant worklogs")
            return all_worklogs

        except Exception as e:
            logger.error(f"Error searching issues with worklogs: {e}")
            raise

    def _is_worklog_in_date_range(
        self, worklog: Dict, from_date: datetime, to_date: datetime
    ) -> bool:
        """Check if worklog falls within the specified date range."""
        try:
            # Jira worklog dates are in format: "2023-10-15T10:30:00.000+0000"
            started = worklog.get("started", "")
            if not started:
                return False

            # Parse the date part only
            worklog_date = datetime.strptime(started[:10], "%Y-%m-%d")
            return from_date.date() <= worklog_date.date() <= to_date.date()

        except Exception as e:
            logger.warning(f"Could not parse worklog date {started}: {e}")
            return False

    def get_issue_details(self, issue_key: str) -> Optional[Dict]:
        """Get detailed information about a specific issue."""
        endpoint = f"/rest/api/3/issue/{issue_key}"
        params = {"fields": "summary,project,issuetype,labels,status"}

        try:
            response = self._make_request("GET", endpoint, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    f"Failed to get issue {issue_key}: {response.status_code}"
                )
                return None
        except Exception as e:
            logger.error(f"Error fetching issue {issue_key}: {e}")
            return None

    def get_issue_worklogs(
        self, issue_key: str, bypass_cache: bool = True
    ) -> List[Dict]:
        """Get all worklogs for a specific issue."""
        endpoint = f"/rest/api/3/issue/{issue_key}/worklog"

        # Add cache-busting parameter
        params = {}
        if bypass_cache:
            import time

            params["_"] = int(time.time() * 1000)  # Cache buster

        try:
            response = self._make_request("GET", endpoint, params=params)
            if response.status_code == 200:
                data = response.json()
                worklogs = data.get("worklogs", [])

                # Add issue context to each worklog
                for worklog in worklogs:
                    worklog["issue"] = {
                        "key": issue_key,
                        "projectKey": issue_key.split("-")[
                            0
                        ],  # Extract project key from issue key
                    }

                logger.info(f"Retrieved {len(worklogs)} worklogs for issue {issue_key}")
                return worklogs
            else:
                logger.warning(
                    f"Failed to get worklogs for {issue_key}: {response.status_code}"
                )
                return []
        except Exception as e:
            logger.error(f"Error fetching worklogs for {issue_key}: {e}")
            return []

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make a request to the Jira API."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.request(
                method, url, headers=self.headers, timeout=30, **kwargs
            )
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
