"""Minimal Tempo API client for worklog retrieval."""

import logging
from datetime import datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)


class TempoClient:
    """Simple Tempo API client."""

    def __init__(self, api_token: str) -> None:
        """Initialize Tempo client.

        Args:
            api_token: Tempo API authentication token
        """
        self.api_token = api_token
        self.base_url = "https://api.tempo.io/4"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    def get_worklogs(self, from_date: datetime, to_date: datetime) -> list[dict[str, Any]]:
        """Get worklogs for date range.

        Args:
            from_date: Start date
            to_date: End date

        Returns:
            List of worklog entries
        """
        url = f"{self.base_url}/worklogs"
        params = {
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
            "limit": "5000",
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            worklogs = data.get("results", [])
            logger.info(f"Retrieved {len(worklogs)} worklogs from Tempo")
            return worklogs
        except requests.RequestException as e:
            logger.error(f"Error fetching worklogs from Tempo: {e}")
            raise

    def test_connection(self) -> bool:
        """Test if API connection works.

        Returns:
            True if connection is successful
        """
        try:
            response = requests.get(f"{self.base_url}/myself", headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Tempo connection test failed: {e}")
            return False
