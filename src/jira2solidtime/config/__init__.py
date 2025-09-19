"""Configuration management module for jira2solidtime."""

import os
import yaml
from dotenv import load_dotenv
from .database import ConfigDatabase
from .manager import (
    ConfigManager,
    AppConfig,
    JiraConfig,
    SolidtimeConfig,
    SyncConfig,
    MonitoringConfig,
)

load_dotenv()

# Global config manager instance
_config_manager = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def load_config() -> AppConfig:
    """Load configuration using the new ConfigManager with mapping rules."""
    config_manager = get_config_manager()

    # Load core configuration from database/environment
    app_config = config_manager.load_app_config()

    # Load mapping rules from YAML file
    try:
        with open("config/mapping_rules.yaml", "r") as f:
            mapping_rules = yaml.safe_load(f)
    except FileNotFoundError:
        mapping_rules = {"project_mappings": {}}

    # Parse project mappings from environment (legacy support)
    project_mappings_str = os.getenv("PROJECT_MAPPINGS", "")
    env_project_mappings = {}
    if project_mappings_str:
        for mapping in project_mappings_str.split(";"):
            if "|" in mapping:
                key, name = mapping.split("|", 1)
                env_project_mappings[key.strip()] = name.strip()

    # Merge .env mappings with YAML mappings (.env takes precedence for flexibility)
    final_project_mappings = {
        **mapping_rules.get("project_mappings", {}),
        **env_project_mappings,
    }

    # Update mapping rules with final project mappings
    mapping_rules["project_mappings"] = final_project_mappings

    # If no explicit project filter, use project mappings keys as filter
    if not app_config.sync.filter_project_keys and final_project_mappings:
        app_config.sync.filter_project_keys = list(final_project_mappings.keys())

    # Add mapping rules to config (for backward compatibility)
    app_config.mapping_rules = mapping_rules

    return app_config


__all__ = [
    "ConfigDatabase",
    "ConfigManager",
    "AppConfig",
    "JiraConfig",
    "SolidtimeConfig",
    "SyncConfig",
    "MonitoringConfig",
    "get_config_manager",
    "load_config",
]
