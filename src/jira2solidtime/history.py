"""Sync history tracking using SQLite."""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class History:
    """Tracks synchronization history."""

    def __init__(self, db_path: str = "data/history.db") -> None:
        """Initialize history database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS syncs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    created INTEGER DEFAULT 0,
                    updated INTEGER DEFAULT 0,
                    deleted INTEGER DEFAULT 0,
                    failed INTEGER DEFAULT 0,
                    total INTEGER DEFAULT 0,
                    error TEXT,
                    duration_seconds REAL DEFAULT 0,
                    actions TEXT
                )
                """
            )
            conn.commit()
            logger.debug(f"Initialized history database at {self.db_path}")

    def record_sync(
        self,
        success: bool,
        created: int = 0,
        updated: int = 0,
        deleted: int = 0,
        failed: int = 0,
        total: int = 0,
        error: str = "",
        duration_seconds: float = 0,
        actions: list[dict[str, Any]] | None = None,
    ) -> int:
        """Record a sync operation.

        Args:
            success: Whether sync was successful
            created: Number of created entries
            updated: Number of updated entries
            deleted: Number of deleted entries
            failed: Number of failed entries
            total: Total entries processed
            error: Error message if failed
            duration_seconds: Sync duration in seconds
            actions: Detailed list of sync actions

        Returns:
            ID of recorded sync
        """
        import json

        actions_json = json.dumps(actions) if actions else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO syncs (timestamp, success, created, updated, deleted, failed, total, error, duration_seconds, actions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(),
                    success,
                    created,
                    updated,
                    deleted,
                    failed,
                    total,
                    error,
                    duration_seconds,
                    actions_json,
                ),
            )
            conn.commit()
            sync_id = cursor.lastrowid
            logger.info(
                f"Recorded sync #{sync_id}: success={success}, created={created}, "
                f"updated={updated}, deleted={deleted}"
            )
            return int(sync_id) if sync_id is not None else -1

    def get_last_syncs(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get last N syncs.

        Args:
            limit: Number of syncs to retrieve

        Returns:
            List of sync records
        """
        import json

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM syncs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

            syncs = []
            for row in rows:
                sync = dict(row)
                # Parse actions JSON if present
                if sync.get("actions"):
                    try:
                        sync["actions"] = json.loads(sync["actions"])
                    except Exception:
                        sync["actions"] = []
                else:
                    sync["actions"] = []
                syncs.append(sync)

            return syncs

    def get_sync_stats(self) -> dict[str, Any]:
        """Get overall sync statistics.

        Returns:
            Dictionary of statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            stats = conn.execute(
                """
                SELECT
                    COUNT(*) as total_syncs,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                    SUM(created) as total_created,
                    SUM(updated) as total_updated,
                    SUM(deleted) as total_deleted,
                    SUM(failed) as total_failed,
                    AVG(duration_seconds) as avg_duration
                FROM syncs
                """
            ).fetchone()

            return {
                "total_syncs": stats[0] or 0,
                "successful": stats[1] or 0,
                "failed": stats[2] or 0,
                "total_created": stats[3] or 0,
                "total_updated": stats[4] or 0,
                "total_deleted": stats[5] or 0,
                "total_failed": stats[6] or 0,
                "avg_duration": stats[7] or 0,
            }

    def clear_old_records(self, days: int = 90) -> None:
        """Delete sync records older than N days.

        Args:
            days: Number of days to keep
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                DELETE FROM syncs
                WHERE datetime(timestamp) < datetime('now', ? || ' days')
                """,
                (f"-{days}",),
            )
            conn.commit()
            logger.info(f"Cleaned up sync records older than {days} days")
