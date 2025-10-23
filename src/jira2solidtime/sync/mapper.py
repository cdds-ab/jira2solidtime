"""Project mapping between Jira and Solidtime."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class Mapper:
    """Maps Jira projects to Solidtime projects."""

    def __init__(self, mappings: dict[str, str]) -> None:
        """Initialize mapper with project mappings.

        Args:
            mappings: Dictionary of Jira key -> Solidtime project name
        """
        self.mappings = mappings
        logger.info(f"Initialized mapper with {len(mappings)} project mappings")

    def map_project(self, jira_key: str) -> Optional[str]:
        """Map Jira project key to Solidtime project name.

        Args:
            jira_key: Jira project key

        Returns:
            Solidtime project name or None if not mapped
        """
        mapped = self.mappings.get(jira_key)
        if mapped:
            logger.debug(f"Mapped {jira_key} -> {mapped}")
        else:
            logger.debug(f"No mapping found for {jira_key}")
        return mapped

    def add_mapping(self, jira_key: str, solidtime_name: str) -> None:
        """Add a project mapping.

        Args:
            jira_key: Jira project key
            solidtime_name: Solidtime project name
        """
        self.mappings[jira_key] = solidtime_name
        logger.info(f"Added mapping: {jira_key} -> {solidtime_name}")

    def get_all_mappings(self) -> dict[str, str]:
        """Get all project mappings.

        Returns:
            Dictionary of all mappings
        """
        return self.mappings.copy()
