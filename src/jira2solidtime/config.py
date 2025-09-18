import os
from dataclasses import dataclass
from typing import Optional, List
import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class JiraConfig:
    base_url: str
    api_token: str
    user_email: str
    # Optional Tempo configuration
    organization_id: Optional[str] = None
    tempo_api_token: Optional[str] = None


@dataclass
class SolidtimeConfig:
    base_url: str
    api_token: str
    organization_id: Optional[str] = None


@dataclass
class SyncConfig:
    days_back: int = 30
    dry_run: bool = True
    log_level: str = "INFO"
    # Filtering options
    filter_user_email: Optional[str] = None
    filter_project_keys: Optional[List[str]] = None
    # Data directories
    data_dir: str = "./data"
    log_dir: str = "./logs"


@dataclass
class AppConfig:
    jira: JiraConfig
    solidtime: SolidtimeConfig
    sync: SyncConfig
    mapping_rules: dict


def load_config() -> AppConfig:
    """Load configuration from environment variables and mapping rules."""

    # Load mapping rules
    with open("config/mapping_rules.yaml", "r") as f:
        mapping_rules = yaml.safe_load(f)

    jira_config = JiraConfig(
        base_url=os.getenv("JIRA_BASE_URL") or "",
        api_token=os.getenv("JIRA_API_TOKEN") or "",
        user_email=os.getenv("JIRA_USER_EMAIL") or "",
        organization_id=os.getenv("JIRA_ORGANISATION_ID"),
        tempo_api_token=os.getenv("TEMPO_API_TOKEN") or "",
    )

    solidtime_config = SolidtimeConfig(
        base_url=os.getenv("SOLIDTIME_BASE_URL") or "",
        api_token=os.getenv("SOLIDTIME_API_TOKEN") or "",
        organization_id=os.getenv("SOLIDTIME_ORGANIZATION_ID"),
    )

    # Parse project keys from comma-separated string
    project_keys_str = os.getenv("FILTER_PROJECT_KEYS", "")
    filter_project_keys = (
        [key.strip() for key in project_keys_str.split(",") if key.strip()]
        if project_keys_str
        else None
    )

    # Parse project mappings from .env (format: "KEY1|Name1;KEY2|Name2")
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
    if not filter_project_keys and final_project_mappings:
        filter_project_keys = list(final_project_mappings.keys())

    sync_config = SyncConfig(
        days_back=int(os.getenv("SYNC_DAYS_BACK", "30")),
        dry_run=os.getenv("DRY_RUN", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        filter_user_email=os.getenv("FILTER_USER_EMAIL"),
        filter_project_keys=filter_project_keys,
        data_dir=os.getenv("DATA_DIR", "./data"),
        log_dir=os.getenv("LOG_DIR", "./logs"),
    )

    return AppConfig(
        jira=jira_config,
        solidtime=solidtime_config,
        sync=sync_config,
        mapping_rules=mapping_rules,
    )
