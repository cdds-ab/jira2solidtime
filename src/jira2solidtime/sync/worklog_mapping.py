"""Worklog ID mapping system for deduplication using SQLite.

Tracks Tempo worklog IDs → Solidtime time entry IDs to prevent
duplicate syncs and enable update detection.

Uses SQLite with WAL mode for crash-safe atomic writes.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class WorklogMapping:
    """Manages mapping between Tempo worklog IDs and Solidtime time entry IDs.

    Uses SQLite database (shared with history.db) for crash-safe persistence.
    """

    def __init__(self, db_path: str = "data/history.db") -> None:
        """Initialize worklog mapping.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._migrate_from_json()

    def _init_db(self) -> None:
        """Initialize database schema if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            # Enable WAL mode for crash safety
            conn.execute("PRAGMA journal_mode=WAL")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS worklog_mappings (
                    tempo_worklog_id TEXT PRIMARY KEY,
                    solidtime_entry_id TEXT NOT NULL,
                    issue_key TEXT,
                    last_duration INTEGER,
                    last_description TEXT,
                    last_date TEXT,
                    created_at TEXT,
                    last_check TEXT,
                    processed INTEGER DEFAULT 0
                )
                """
            )
            conn.commit()
            logger.debug(f"Initialized worklog mapping database at {self.db_path}")

    def _migrate_from_json(self) -> None:
        """Migrate existing JSON mappings to SQLite (one-time migration)."""
        json_path = self.db_path.parent / "worklog_mapping.json"
        if not json_path.exists():
            return

        try:
            with open(json_path) as f:
                data = json.load(f)
                mappings = data.get("mappings", {})

            if not mappings:
                return

            # Check if migration is needed (any entries in JSON not in SQLite)
            with sqlite3.connect(self.db_path) as conn:
                existing = conn.execute("SELECT COUNT(*) FROM worklog_mappings").fetchone()[0]

                if existing > 0:
                    logger.debug("SQLite already has mappings, skipping JSON migration")
                    return

                # Migrate all entries
                logger.info(f"Migrating {len(mappings)} mappings from JSON to SQLite...")
                for tempo_id, mapping in mappings.items():
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO worklog_mappings
                        (tempo_worklog_id, solidtime_entry_id, issue_key, last_duration,
                         last_description, last_date, created_at, last_check, processed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                        """,
                        (
                            str(tempo_id),
                            mapping.get("solidtime_entry_id", ""),
                            mapping.get("issue_key", ""),
                            mapping.get("last_duration"),
                            mapping.get("last_description"),
                            mapping.get("last_date"),
                            mapping.get("created_at"),
                            mapping.get("last_check"),
                        ),
                    )
                conn.commit()
                logger.info(f"Successfully migrated {len(mappings)} mappings to SQLite")

            # Rename JSON file to backup
            backup_path = json_path.with_suffix(".json.migrated")
            json_path.rename(backup_path)
            logger.info(f"Renamed {json_path} to {backup_path}")

        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not migrate JSON mappings: {e}")

    def get_solidtime_entry_id(self, tempo_worklog_id: str) -> Optional[str]:
        """Get Solidtime entry ID for a Tempo worklog.

        Args:
            tempo_worklog_id: Tempo worklog ID (from tempoWorklogId field)

        Returns:
            Solidtime entry ID if mapped, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT solidtime_entry_id FROM worklog_mappings WHERE tempo_worklog_id = ?",
                (str(tempo_worklog_id),),
            ).fetchone()
            return row[0] if row else None

    def add_mapping(
        self,
        tempo_worklog_id: str,
        solidtime_entry_id: str,
        issue_key: str,
        duration_minutes: Optional[int] = None,
        description: Optional[str] = None,
        date: Optional[str] = None,
    ) -> None:
        """Record a mapping between Tempo worklog and Solidtime entry.

        Args:
            tempo_worklog_id: Tempo worklog ID
            solidtime_entry_id: Solidtime time entry ID
            issue_key: Jira issue key for reference
            duration_minutes: Last synced duration (for change detection)
            description: Last synced description (for change detection)
            date: Last synced date (for change detection)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO worklog_mappings
                (tempo_worklog_id, solidtime_entry_id, issue_key, last_duration,
                 last_description, last_date, created_at, last_check, processed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    str(tempo_worklog_id),
                    solidtime_entry_id,
                    issue_key,
                    duration_minutes,
                    description,
                    date,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
        logger.debug(f"Mapped Tempo {tempo_worklog_id} -> Solidtime {solidtime_entry_id}")

    def is_already_synced(self, tempo_worklog_id: str) -> bool:
        """Check if a Tempo worklog was already synced to Solidtime.

        Args:
            tempo_worklog_id: Tempo worklog ID

        Returns:
            True if already mapped, False otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM worklog_mappings WHERE tempo_worklog_id = ?",
                (str(tempo_worklog_id),),
            ).fetchone()
            return row is not None

    def get_stats(self) -> dict[str, Any]:
        """Get mapping statistics.

        Returns:
            Dictionary with mapping counts
        """
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM worklog_mappings").fetchone()[0]
            unique_issues = conn.execute(
                "SELECT COUNT(DISTINCT issue_key) FROM worklog_mappings"
            ).fetchone()[0]
            return {
                "total_mappings": total,
                "unique_issues": unique_issues,
            }

    def mark_processed(self, tempo_worklog_id: str) -> None:
        """Mark a mapping as processed in current sync.

        Args:
            tempo_worklog_id: Tempo worklog ID
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE worklog_mappings SET processed = 1 WHERE tempo_worklog_id = ?",
                (str(tempo_worklog_id),),
            )
            conn.commit()

    def reset_processed(self) -> None:
        """Reset processed flag for all mappings (call at start of sync)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE worklog_mappings SET processed = 0")
            conn.commit()

    def get_unprocessed_mappings(self) -> list[tuple[str, dict[str, Any]]]:
        """Get mappings that were not processed (deleted worklogs).

        Returns:
            List of (tempo_worklog_id, mapping) tuples for unprocessed entries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM worklog_mappings WHERE processed = 0").fetchall()

            return [
                (
                    row["tempo_worklog_id"],
                    {
                        "solidtime_entry_id": row["solidtime_entry_id"],
                        "issue_key": row["issue_key"],
                        "last_duration": row["last_duration"],
                        "last_description": row["last_description"],
                        "last_date": row["last_date"],
                        "created_at": row["created_at"],
                        "last_check": row["last_check"],
                    },
                )
                for row in rows
            ]

    def remove_mapping(self, tempo_worklog_id: str) -> None:
        """Remove a mapping.

        Args:
            tempo_worklog_id: Tempo worklog ID
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM worklog_mappings WHERE tempo_worklog_id = ?",
                (str(tempo_worklog_id),),
            )
            conn.commit()
        logger.debug(f"Removed mapping for Tempo {tempo_worklog_id}")

    def has_changes(
        self,
        tempo_worklog_id: str,
        duration_minutes: int,
        description: str,
        date_str: str,
    ) -> bool:
        """Check if worklog data has changed since last sync.

        Args:
            tempo_worklog_id: Tempo worklog ID
            duration_minutes: Current duration in minutes
            description: Current description
            date_str: Current date as ISO string

        Returns:
            True if data changed or no previous sync data, False otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT last_duration, last_description, last_date
                FROM worklog_mappings WHERE tempo_worklog_id = ?
                """,
                (str(tempo_worklog_id),),
            ).fetchone()

            if not row:
                return True  # No mapping = first sync = has changes

            last_duration, last_description, last_date = row

            # If any value is missing (old mapping format), assume changed
            if last_duration is None or last_description is None or last_date is None:
                return True

            # Check if any field changed
            return (
                duration_minutes != last_duration
                or description != last_description
                or date_str != last_date
            )

    def update_sync_data(
        self,
        tempo_worklog_id: str,
        duration_minutes: int,
        description: str,
        date_str: str,
    ) -> None:
        """Update last synced data for a worklog (after successful UPDATE).

        Args:
            tempo_worklog_id: Tempo worklog ID
            duration_minutes: Current duration in minutes
            description: Current description
            date_str: Current date as ISO string
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE worklog_mappings
                SET last_duration = ?, last_description = ?, last_date = ?, last_check = ?
                WHERE tempo_worklog_id = ?
                """,
                (
                    duration_minutes,
                    description,
                    date_str,
                    datetime.now().isoformat(),
                    str(tempo_worklog_id),
                ),
            )
            conn.commit()
        logger.debug(f"Updated sync data for Tempo {tempo_worklog_id}")

    def needs_existence_check(self, tempo_worklog_id: str, hours: int = 24) -> bool:
        """Check if entry needs existence verification (last check >N hours ago).

        Args:
            tempo_worklog_id: Tempo worklog ID
            hours: Hours since last check to trigger verification (default: 24)

        Returns:
            True if existence check is needed, False otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT last_check FROM worklog_mappings WHERE tempo_worklog_id = ?",
                (str(tempo_worklog_id),),
            ).fetchone()

            if not row or not row[0]:
                return True  # No last check recorded = needs check

            try:
                last_check = datetime.fromisoformat(row[0])
                hours_since_check = (datetime.now() - last_check).total_seconds() / 3600
                return hours_since_check > hours
            except (ValueError, TypeError):
                return True  # Invalid timestamp = needs check

    def update_last_check(self, tempo_worklog_id: str) -> None:
        """Update last existence check timestamp.

        Args:
            tempo_worklog_id: Tempo worklog ID
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE worklog_mappings SET last_check = ? WHERE tempo_worklog_id = ?",
                (datetime.now().isoformat(), str(tempo_worklog_id)),
            )
            conn.commit()
        logger.debug(f"Updated last check for Tempo {tempo_worklog_id}")

    def save(self) -> None:
        """Compatibility method - SQLite auto-commits, so this is a no-op.

        Kept for API compatibility with code that calls save() after batch operations.
        """
        # SQLite auto-commits within each method, no explicit save needed
        pass
