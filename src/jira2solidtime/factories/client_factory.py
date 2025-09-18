"""Factory for creating API clients."""

from ..api.tempo_client import TempoClient
from ..api.jira_client import JiraClient
from ..api.solidtime_client import SolidtimeClient
from ..config import AppConfig


class ClientFactory:
    """Factory for creating API clients with configuration."""

    @staticmethod
    def create_tempo_client(config: AppConfig) -> TempoClient:
        """Create Tempo API client."""
        if not config.jira.tempo_api_token:
            raise ValueError("TEMPO_API_TOKEN is required")
        if not config.jira.base_url:
            raise ValueError("JIRA_BASE_URL is required")
        return TempoClient(config.jira.tempo_api_token, config.jira.base_url)

    @staticmethod
    def create_jira_client(config: AppConfig) -> JiraClient:
        """Create Jira API client."""
        if not config.jira.base_url:
            raise ValueError("JIRA_BASE_URL is required")
        if not config.jira.user_email:
            raise ValueError("JIRA_USER_EMAIL is required")
        if not config.jira.api_token:
            raise ValueError("JIRA_API_TOKEN is required")
        return JiraClient(
            config.jira.base_url, config.jira.user_email, config.jira.api_token
        )

    @staticmethod
    def create_solidtime_client(config: AppConfig) -> SolidtimeClient:
        """Create Solidtime API client."""
        if not config.solidtime.api_token:
            raise ValueError("SOLIDTIME_API_TOKEN is required")
        if not config.solidtime.base_url:
            raise ValueError("SOLIDTIME_BASE_URL is required")
        if not config.solidtime.organization_id:
            raise ValueError("SOLIDTIME_ORGANIZATION_ID is required")
        return SolidtimeClient(
            config.solidtime.api_token,
            config.solidtime.base_url,
            config.solidtime.organization_id,
        )
