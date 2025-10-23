"""Simple JSON configuration loader for jira2solidtime."""

import json
from pathlib import Path
from typing import Any, Dict


class Config:
    """Configuration container loaded from JSON file."""

    def __init__(self, config_path: str = "config.json") -> None:
        """Initialize configuration from JSON file.

        Args:
            config_path: Path to config.json file
        """
        self.path = Path(config_path)
        self.data: Dict[str, Any] = {}

        if self.path.exists():
            with open(self.path) as f:
                self.data = json.load(f)
        else:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

    @property
    def jira(self) -> Dict[str, str]:
        """Get Jira configuration."""
        return self.data.get("jira", {})

    @property
    def tempo(self) -> Dict[str, str]:
        """Get Tempo configuration."""
        return self.data.get("tempo", {})

    @property
    def solidtime(self) -> Dict[str, str]:
        """Get Solidtime configuration."""
        return self.data.get("solidtime", {})

    @property
    def sync(self) -> Dict[str, Any]:
        """Get sync configuration."""
        return self.data.get("sync", {})

    @property
    def mappings(self) -> Dict[str, str]:
        """Get project mappings (Jira Key -> Solidtime Project Name)."""
        return self.data.get("mappings", {})

    @property
    def web(self) -> Dict[str, Any]:
        """Get web UI configuration."""
        return self.data.get("web", {"port": 8080})

    def validate(self) -> tuple[bool, list[str]]:
        """Validate required configuration fields.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors: list[str] = []

        # Check required Jira fields
        if not self.jira.get("base_url"):
            errors.append("jira.base_url is required")
        if not self.jira.get("api_token"):
            errors.append("jira.api_token is required")
        if not self.jira.get("user_email"):
            errors.append("jira.user_email is required")

        # Check required Tempo fields
        if not self.tempo.get("api_token"):
            errors.append("tempo.api_token is required")

        # Check required Solidtime fields
        if not self.solidtime.get("base_url"):
            errors.append("solidtime.base_url is required")
        if not self.solidtime.get("api_token"):
            errors.append("solidtime.api_token is required")
        if not self.solidtime.get("organization_id"):
            errors.append("solidtime.organization_id is required")

        return len(errors) == 0, errors

    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return self.data.copy()
