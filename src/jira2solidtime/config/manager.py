"""Configuration manager that handles SQLite database and environment variables."""

import os
from typing import Any, Dict, List, Optional
from dataclasses import field
from dataclasses import dataclass
from .database import ConfigDatabase


@dataclass
class JiraConfig:
    base_url: str
    api_token: str
    user_email: str
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
    filter_user_email: Optional[str] = None
    filter_project_keys: Optional[List[str]] = None
    data_dir: str = "./data"
    log_dir: str = "./logs"
    schedule: str = "0 */10 6-22 * * *"
    health_check_schedule: str = "0 */1 * * * *"


@dataclass
class MonitoringConfig:
    enabled: bool = True
    alert_threshold_seconds: int = 900
    sync_start_hour: int = 6
    sync_end_hour: int = 22
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    teams_webhook_url: Optional[str] = None


@dataclass
class AppConfig:
    jira: JiraConfig
    solidtime: SolidtimeConfig
    sync: SyncConfig
    monitoring: MonitoringConfig
    mapping_rules: dict = field(default_factory=dict)  # For backward compatibility


class ConfigManager:
    """Configuration manager with SQLite database and environment variable fallback."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize configuration manager.

        Args:
            db_path: Path to SQLite configuration database
        """
        self.db = ConfigDatabase(db_path)
        self._migrate_env_to_db()

    def _migrate_env_to_db(self) -> None:
        """Migrate environment variables to database on first run."""
        # Check if we've already migrated
        if self.db.get_config("system.migrated_from_env", False):
            return

        # Migrate environment variables to database
        env_mappings = {
            # Jira configuration
            "jira.base_url": ("JIRA_BASE_URL", ""),
            "jira.api_token": ("JIRA_API_TOKEN", ""),
            "jira.user_email": ("JIRA_USER_EMAIL", ""),
            "jira.organization_id": ("JIRA_ORGANISATION_ID", None),
            "jira.tempo_api_token": ("TEMPO_API_TOKEN", ""),
            # Solidtime configuration
            "solidtime.base_url": ("SOLIDTIME_BASE_URL", ""),
            "solidtime.api_token": ("SOLIDTIME_API_TOKEN", ""),
            "solidtime.organization_id": ("SOLIDTIME_ORGANIZATION_ID", None),
            # Sync configuration
            "sync.days_back": ("SYNC_DAYS_BACK", 30),
            "sync.dry_run": ("DRY_RUN", True),
            "sync.log_level": ("LOG_LEVEL", "INFO"),
            "sync.filter_user_email": ("FILTER_USER_EMAIL", None),
            "sync.data_dir": ("DATA_DIR", "./data"),
            "sync.log_dir": ("LOG_DIR", "./logs"),
            "sync.schedule": ("SYNC_SCHEDULE", "0 */10 6-22 * * *"),
            "sync.health_check_schedule": ("HEALTH_CHECK_SCHEDULE", "0 */1 * * * *"),
            # Monitoring configuration
            "monitoring.alert_threshold_seconds": ("SYNC_ALERT_THRESHOLD", 900),
            "monitoring.sync_start_hour": ("SYNC_START_HOUR", 6),
            "monitoring.sync_end_hour": ("SYNC_END_HOUR", 22),
            "monitoring.telegram_bot_token": ("TELEGRAM_BOT_TOKEN", None),
            "monitoring.telegram_chat_id": ("TELEGRAM_CHAT_ID", None),
            "monitoring.teams_webhook_url": ("TEAMS_WEBHOOK_URL", None),
        }

        migrated_any = False
        for db_key, (env_key, default) in env_mappings.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                # Convert string values to appropriate types
                converted_value: Any = env_value
                if db_key.endswith((".dry_run",)):
                    converted_value = env_value.lower() in ("true", "1", "yes", "on")
                elif db_key.endswith(
                    (
                        ".days_back",
                        ".alert_threshold_seconds",
                        ".sync_start_hour",
                        ".sync_end_hour",
                    )
                ):
                    converted_value = int(env_value)

                # Determine category from key
                category = db_key.split(".")[0]

                # Store in database
                self.db.set_config(
                    db_key,
                    converted_value,
                    category=category,
                    description=f"Migrated from environment variable {env_key}",
                )
                migrated_any = True

        # Handle special cases
        project_keys_str = os.getenv("FILTER_PROJECT_KEYS", "")
        if project_keys_str:
            filter_project_keys = [
                key.strip() for key in project_keys_str.split(",") if key.strip()
            ]
            self.db.set_config(
                "sync.filter_project_keys",
                filter_project_keys,
                category="sync",
                description="Migrated from FILTER_PROJECT_KEYS environment variable",
            )
            migrated_any = True

        # Mark migration as complete
        self.db.set_config(
            "system.migrated_from_env",
            True,
            category="system",
            description="Environment variable migration completed",
        )

        if migrated_any:
            print("✅ Migrated environment variables to configuration database")

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value with environment variable fallback.

        Args:
            key: Configuration key (e.g., 'jira.base_url')
            default: Default value if not found

        Returns:
            Configuration value
        """
        # Try database first
        db_value = self.db.get_config(key)
        if db_value is not None:
            return db_value

        # Fallback to environment variable
        env_key = key.replace(".", "_").upper()
        env_value = os.getenv(env_key)
        if env_value is not None:
            # Auto-convert common types
            if key.endswith(".dry_run"):
                return env_value.lower() in ("true", "1", "yes", "on")
            elif key.endswith(
                (
                    ".days_back",
                    ".alert_threshold_seconds",
                    ".sync_start_hour",
                    ".sync_end_hour",
                )
            ):
                return int(env_value)
            return env_value

        return default

    def set_config(self, key: str, value: Any, category: Optional[str] = None) -> None:
        """Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value
            category: Configuration category (inferred from key if not provided)
        """
        if category is None:
            category = key.split(".")[0] if "." in key else "general"

        self.db.set_config(key, value, category=category)

    def load_app_config(self) -> AppConfig:
        """Load complete application configuration.

        Returns:
            AppConfig instance with all configuration sections
        """
        # Load Jira configuration
        jira_config = JiraConfig(
            base_url=self.get_config("jira.base_url", ""),
            api_token=self.get_config("jira.api_token", ""),
            user_email=self.get_config("jira.user_email", ""),
            organization_id=self.get_config("jira.organization_id"),
            tempo_api_token=self.get_config("jira.tempo_api_token", ""),
        )

        # Load Solidtime configuration
        solidtime_config = SolidtimeConfig(
            base_url=self.get_config("solidtime.base_url", ""),
            api_token=self.get_config("solidtime.api_token", ""),
            organization_id=self.get_config("solidtime.organization_id"),
        )

        # Load Sync configuration
        sync_config = SyncConfig(
            days_back=self.get_config("sync.days_back", 30),
            dry_run=self.get_config("sync.dry_run", True),
            log_level=self.get_config("sync.log_level", "INFO"),
            filter_user_email=self.get_config("sync.filter_user_email"),
            filter_project_keys=self.get_config("sync.filter_project_keys"),
            data_dir=self.get_config("sync.data_dir", "./data"),
            log_dir=self.get_config("sync.log_dir", "./logs"),
            schedule=self.get_config("sync.schedule", "0 */10 6-22 * * *"),
            health_check_schedule=self.get_config(
                "sync.health_check_schedule", "0 */1 * * * *"
            ),
        )

        # Load Monitoring configuration
        monitoring_config = MonitoringConfig(
            enabled=self.get_config("monitoring.enabled", True),
            alert_threshold_seconds=self.get_config(
                "monitoring.alert_threshold_seconds", 900
            ),
            sync_start_hour=self.get_config("monitoring.sync_start_hour", 6),
            sync_end_hour=self.get_config("monitoring.sync_end_hour", 22),
            telegram_bot_token=self.get_config("monitoring.telegram_bot_token"),
            telegram_chat_id=self.get_config("monitoring.telegram_chat_id"),
            teams_webhook_url=self.get_config("monitoring.teams_webhook_url"),
        )

        return AppConfig(
            jira=jira_config,
            solidtime=solidtime_config,
            sync=sync_config,
            monitoring=monitoring_config,
        )

    def list_config(self, category: Optional[str] = None) -> Dict[str, Any]:
        """List configuration entries.

        Args:
            category: Filter by category (sync, monitoring, jira, solidtime)

        Returns:
            Dictionary of configuration entries
        """
        return self.db.list_config(category=category)

    def export_config(self) -> Dict[str, Any]:
        """Export all configuration for backup/restore."""
        return self.db.export_config()

    def import_config(
        self, config_data: Dict[str, Any], overwrite: bool = False
    ) -> None:
        """Import configuration from backup."""
        self.db.import_config(config_data, overwrite=overwrite)
