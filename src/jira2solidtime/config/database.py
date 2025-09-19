"""Configuration database management for jira2solidtime."""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager


class ConfigDatabase:
    """SQLite-based configuration database with migration support."""

    CURRENT_SCHEMA_VERSION = 1

    def __init__(self, db_path: Optional[str] = None):
        """Initialize configuration database.

        Args:
            db_path: Path to SQLite database file. Defaults to data/config.db
        """
        if db_path is None:
            data_dir = Path(os.getenv("DATA_DIR", "./data"))
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(data_dir / "config.db")
        else:
            self.db_path = db_path
        self.init_database()

    @contextmanager
    def get_connection(self):
        """Get database connection with proper cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_database(self) -> None:
        """Initialize database schema and run migrations if needed."""
        with self.get_connection() as conn:
            self._create_schema(conn)
            current_version = self._get_schema_version(conn)

            if current_version < self.CURRENT_SCHEMA_VERSION:
                self._run_migrations(conn, current_version)

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        """Create initial database schema."""
        conn.executescript(
            """
            -- Schema version tracking
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            );

            -- Configuration entries with JSON values
            CREATE TABLE IF NOT EXISTS config_entries (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,  -- JSON string
                category TEXT NOT NULL DEFAULT 'general',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Audit log for configuration changes
            CREATE TABLE IF NOT EXISTS config_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT NOT NULL,
                old_value TEXT,  -- JSON string
                new_value TEXT,  -- JSON string
                changed_by TEXT DEFAULT 'system',
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action TEXT NOT NULL  -- 'create', 'update', 'delete'
            );

            -- Indexes for better performance
            CREATE INDEX IF NOT EXISTS idx_config_category ON config_entries(category);
            CREATE INDEX IF NOT EXISTS idx_audit_key_time ON config_audit_log(config_key, changed_at);

            -- Triggers for automatic timestamp updates
            CREATE TRIGGER IF NOT EXISTS update_config_timestamp
                AFTER UPDATE ON config_entries
            BEGIN
                UPDATE config_entries
                SET updated_at = CURRENT_TIMESTAMP
                WHERE key = NEW.key;
            END;

            -- Trigger for audit logging
            CREATE TRIGGER IF NOT EXISTS audit_config_changes
                AFTER UPDATE ON config_entries
            BEGIN
                INSERT INTO config_audit_log (config_key, old_value, new_value, action)
                VALUES (NEW.key, OLD.value, NEW.value, 'update');
            END;

            CREATE TRIGGER IF NOT EXISTS audit_config_inserts
                AFTER INSERT ON config_entries
            BEGIN
                INSERT INTO config_audit_log (config_key, old_value, new_value, action)
                VALUES (NEW.key, NULL, NEW.value, 'create');
            END;

            CREATE TRIGGER IF NOT EXISTS audit_config_deletes
                AFTER DELETE ON config_entries
            BEGIN
                INSERT INTO config_audit_log (config_key, old_value, new_value, action)
                VALUES (OLD.key, OLD.value, NULL, 'delete');
            END;
        """
        )

        # Insert initial schema version if not exists
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations (version, description)
            VALUES (1, 'Initial schema with config_entries, audit_log, and triggers')
        """
        )
        conn.commit()

    def _get_schema_version(self, conn: sqlite3.Connection) -> int:
        """Get current schema version."""
        try:
            result = conn.execute(
                "SELECT MAX(version) FROM schema_migrations"
            ).fetchone()
            return result[0] if result and result[0] is not None else 0
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            return 0

    def _run_migrations(self, conn: sqlite3.Connection, from_version: int) -> None:
        """Run database migrations from specified version to current."""
        # Future migrations would go here
        # Example:
        # if from_version < 2:
        #     self._migrate_to_v2(conn)
        pass

    def set_config(
        self, key: str, value: Any, category: str = "general", description: str = ""
    ) -> None:
        """Set configuration value.

        Args:
            key: Configuration key (e.g., 'jira.base_url')
            value: Configuration value (will be JSON serialized)
            category: Configuration category (e.g., 'sync', 'monitoring')
            description: Human-readable description
        """
        json_value = json.dumps(value, ensure_ascii=False)

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO config_entries (key, value, category, description)
                VALUES (?, ?, ?, ?)
            """,
                (key, json_value, category, description),
            )
            conn.commit()

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value (JSON deserialized)
        """
        with self.get_connection() as conn:
            result = conn.execute(
                "SELECT value FROM config_entries WHERE key = ?", (key,)
            ).fetchone()

            if result:
                return json.loads(result["value"])
            return default

    def list_config(
        self, category: Optional[str] = None, pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """List configuration entries.

        Args:
            category: Filter by category
            pattern: Filter keys by pattern (SQL LIKE)

        Returns:
            Dictionary of key-value pairs
        """
        query = "SELECT key, value FROM config_entries WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)

        if pattern:
            query += " AND key LIKE ?"
            params.append(pattern)

        query += " ORDER BY key"

        with self.get_connection() as conn:
            results = conn.execute(query, params).fetchall()
            return {row["key"]: json.loads(row["value"]) for row in results}

    def delete_config(self, key: str) -> bool:
        """Delete configuration entry.

        Args:
            key: Configuration key to delete

        Returns:
            True if key was deleted, False if key didn't exist
        """
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM config_entries WHERE key = ?", (key,))
            conn.commit()
            return cursor.rowcount > 0

    def get_audit_log(
        self, key: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit log entries.

        Args:
            key: Filter by specific config key
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries
        """
        query = """
            SELECT config_key, old_value, new_value, changed_by, changed_at, action
            FROM config_audit_log
        """
        params = []

        if key:
            query += " WHERE config_key = ?"
            params.append(key)

        query += " ORDER BY changed_at DESC LIMIT ?"
        params.append(str(limit))

        with self.get_connection() as conn:
            results = conn.execute(query, params).fetchall()
            return [
                {
                    "config_key": row["config_key"],
                    "old_value": (
                        json.loads(row["old_value"]) if row["old_value"] else None
                    ),
                    "new_value": (
                        json.loads(row["new_value"]) if row["new_value"] else None
                    ),
                    "changed_by": row["changed_by"],
                    "changed_at": row["changed_at"],
                    "action": row["action"],
                }
                for row in results
            ]

    def export_config(self) -> Dict[str, Any]:
        """Export all configuration as JSON-serializable dictionary.

        Returns:
            Dictionary with metadata and config entries
        """
        with self.get_connection() as conn:
            # Get all config entries
            results = conn.execute(
                """
                SELECT key, value, category, description, created_at, updated_at
                FROM config_entries
                ORDER BY key
            """
            ).fetchall()

            config_data = {}
            for row in results:
                config_data[row["key"]] = {
                    "value": json.loads(row["value"]),
                    "category": row["category"],
                    "description": row["description"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }

            return {
                "export_timestamp": datetime.now().isoformat(),
                "schema_version": self._get_schema_version(conn),
                "config_entries": config_data,
            }

    def import_config(
        self, config_data: Dict[str, Any], overwrite: bool = False
    ) -> None:
        """Import configuration from exported data.

        Args:
            config_data: Configuration data from export_config()
            overwrite: Whether to overwrite existing entries
        """
        if "config_entries" not in config_data:
            raise ValueError("Invalid config data format")

        with self.get_connection() as conn:
            for key, entry in config_data["config_entries"].items():
                if not overwrite:
                    # Check if key already exists
                    existing = conn.execute(
                        "SELECT 1 FROM config_entries WHERE key = ?", (key,)
                    ).fetchone()
                    if existing:
                        continue

                # Import the entry
                conn.execute(
                    """
                    INSERT OR REPLACE INTO config_entries (key, value, category, description)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        key,
                        json.dumps(entry["value"], ensure_ascii=False),
                        entry.get("category", "general"),
                        entry.get("description", ""),
                    ),
                )

            conn.commit()
