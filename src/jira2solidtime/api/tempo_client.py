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


class TempoClient:
    def __init__(self, api_token: str, jira_base_url: str):
        self.api_token = api_token
        self.jira_base_url = jira_base_url
        self.base_url = "https://api.tempo.io/4"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (requests.exceptions.Timeout, requests.exceptions.ConnectionError)
        ),
        reraise=True,
    )
    def _make_request_with_retry(
        self, method: str, url: str, **kwargs
    ) -> requests.Response:
        """Make HTTP request with retry logic for transient failures."""
        logger.debug(f"Making {method} request to {url} (with retry)")
        response = requests.request(
            method, url, headers=self.headers, timeout=30, **kwargs
        )
        response.raise_for_status()
        return response

    def get_worklogs(
        self,
        from_date: datetime,
        to_date: datetime,
        project_keys: Optional[List[str]] = None,
        updated_from: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Retrieve worklogs from Tempo API.

        Args:
            from_date: Start date for worklog retrieval
            to_date: End date for worklog retrieval
            project_keys: Optional list of Jira project keys to filter
            updated_from: Optional datetime for incremental sync (get only updated worklogs)

        Returns:
            List of worklog dictionaries
        """
        url = f"{self.base_url}/worklogs"
        params = {
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
            "limit": "5000",  # Max per API v4
        }

        if project_keys:
            # Note: Tempo API v4 requires projectId, not project key
            # We'll filter client-side since we only have project keys
            logger.info(f"Note: Will filter by project keys {project_keys} client-side")

        if updated_from:
            params["updatedFrom"] = updated_from.isoformat()

        logger.info(f"Fetching worklogs from {from_date.date()} to {to_date.date()}")

        try:
            response = self._make_request_with_retry("GET", url, params=params)
            data = response.json()
            worklogs = data.get("results", [])

            logger.info(f"Retrieved {len(worklogs)} worklogs")

            # Handle pagination if needed
            if len(worklogs) == 5000:
                logger.warning(
                    "Retrieved maximum number of worklogs (5000). Consider using smaller date ranges or pagination."
                )

            return worklogs

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching worklogs: {e}")
            if (
                hasattr(e, "response")
                and e.response is not None
                and hasattr(e.response, "text")
            ):
                logger.error(f"Response: {e.response.text}")
            raise

    def get_worklog_by_id(self, worklog_id: str) -> Dict:
        """Get a specific worklog by its ID."""
        url = f"{self.base_url}/worklogs/{worklog_id}"

        try:
            response = self._make_request_with_retry("GET", url)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching worklog {worklog_id}: {e}")
            raise

    def test_connection(self) -> bool:
        """Test the connection to Tempo API."""
        try:
            # Test with a minimal request - get worklogs for today
            today = datetime.now()
            self.get_worklogs(today, today)
            logger.info("Tempo API connection successful")
            return True
        except Exception as e:
            logger.error(f"Tempo API connection failed: {e}")
            return False

    def get_user_worklogs(
        self, user_email: str, from_date: datetime, to_date: datetime
    ) -> List[Dict]:
        """Get worklogs for a specific user."""
        url = f"{self.base_url}/worklogs/user/{user_email}"
        params = {
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
            "limit": "5000",
        }

        try:
            response = self._make_request_with_retry("GET", url, params=params)
            data = response.json()
            worklogs = data.get("results", [])

            logger.info(f"Retrieved {len(worklogs)} worklogs for user {user_email}")
            return worklogs

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching user worklogs: {e}")
            raise

    @staticmethod
    def enrich_worklogs_with_issue_data(
        worklogs: List[Dict], jira_client
    ) -> List[Dict]:
        """Enrich tempo worklogs with issue data from Jira API."""
        enriched_worklogs = []

        for worklog in worklogs:
            issue_url = worklog.get("issue", {}).get("self", "")
            if issue_url and "/issue/" in issue_url:
                # Extract issue ID from URL
                issue_id = issue_url.split("/issue/")[-1]

                # Get issue details from Jira
                try:
                    # Convert issue ID to issue key via Jira API
                    issue_response = jira_client._make_request(
                        "GET", f"/rest/api/3/issue/{issue_id}"
                    )
                    if issue_response.status_code == 200:
                        issue_data = issue_response.json()
                        issue_key = issue_data.get("key", "")
                        project_key = (
                            issue_data.get("fields", {})
                            .get("project", {})
                            .get("key", "")
                        )
                        issue_summary = issue_data.get("fields", {}).get("summary", "")

                        # Add issue data to worklog
                        worklog["issue"]["key"] = issue_key
                        worklog["issue"]["projectKey"] = project_key
                        worklog["issue"]["summary"] = issue_summary

                        logger.debug(
                            f"Enriched worklog: Issue {issue_key} from project {project_key}"
                        )

                except Exception as e:
                    logger.warning(
                        f"Failed to enrich worklog with issue {issue_id}: {e}"
                    )

            enriched_worklogs.append(worklog)

        return enriched_worklogs

    def get_filtered_worklogs(
        self,
        from_date: datetime,
        to_date: datetime,
        user_email: Optional[str] = None,
        project_keys: Optional[List[str]] = None,
        updated_from: Optional[datetime] = None,
        jira_client=None,
    ) -> List[Dict]:
        """
        Get worklogs with optional user and project filtering.

        Args:
            from_date: Start date for worklog retrieval
            to_date: End date for worklog retrieval
            user_email: Optional user email to filter by
            project_keys: Optional list of project keys to filter by
            updated_from: Optional datetime for incremental sync
            jira_client: Jira client for issue data enrichment

        Returns:
            List of filtered worklog dictionaries
        """
        # Get all worklogs (no server-side project filtering with project keys)
        worklogs = self.get_worklogs(from_date, to_date, None, updated_from)

        # Always enrich with issue data if jira_client is provided (needed for smart diff)
        if jira_client:
            worklogs = self.enrich_worklogs_with_issue_data(worklogs, jira_client)

        # Apply client-side filtering
        filtered_worklogs = []
        for worklog in worklogs:
            # Check user filter
            if user_email:
                # TODO: Add email mapping - Compare with accountId
                # Skip user filtering for now since we need email->accountId mapping
                pass

            # Check project filter
            if project_keys:
                worklog_project = worklog.get("issue", {}).get("projectKey", "")
                if worklog_project and worklog_project not in project_keys:
                    continue

            filtered_worklogs.append(worklog)

        filter_info = []
        if user_email:
            filter_info.append(f"user {user_email}")
        if project_keys:
            filter_info.append(f"projects {', '.join(project_keys)}")

        if filter_info:
            logger.info(
                f"Filtered to {len(filtered_worklogs)}/{len(worklogs)} worklogs by {', '.join(filter_info)}"
            )

        return filtered_worklogs
