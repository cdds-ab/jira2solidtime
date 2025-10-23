"""Worklog ID mapping system for deduplication.

Tracks Tempo worklog IDs → Solidtime time entry IDs to prevent
duplicate syncs and enable update detection.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class WorklogMapping:
    """Manages mapping between Tempo worklog IDs and Solidtime time entry IDs."""

    def __init__(self, mapping_file: str = "data/worklog_mapping.json") -> None:
        """Initialize worklog mapping.

        Args:
            mapping_file: Path to JSON file storing mappings
        """
        self.mapping_file = Path(mapping_file)
        self.mapping_file.parent.mkdir(parents=True, exist_ok=True)
        self.mappings: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load existing mappings from file."""
        if not self.mapping_file.exists():
            logger.debug(f"Creating new mapping file: {self.mapping_file}")
            self._save()
            return

        try:
            with open(self.mapping_file) as f:
                data = json.load(f)
                self.mappings = data.get("mappings", {})
                logger.debug(f"Loaded {len(self.mappings)} worklog mappings")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not load mappings: {e}, starting fresh")
            self.mappings = {}
            self._save()

    def _save(self) -> None:
        """Save mappings to file."""
        try:
            data = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "mappings": self.mappings,
            }
            with open(self.mapping_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(self.mappings)} worklog mappings")
        except OSError as e:
            logger.error(f"Failed to save mappings: {e}")

    def get_solidtime_entry_id(self, tempo_worklog_id: str) -> Optional[str]:
        """Get Solidtime entry ID for a Tempo worklog.

        Args:
            tempo_worklog_id: Tempo worklog ID (from tempoWorklogId field)

        Returns:
            Solidtime entry ID if mapped, None otherwise
        """
        mapping = self.mappings.get(str(tempo_worklog_id))
        return mapping.get("solidtime_entry_id") if mapping else None

    def add_mapping(
        self,
        tempo_worklog_id: str,
        solidtime_entry_id: str,
        issue_key: str,
    ) -> None:
        """Record a mapping between Tempo worklog and Solidtime entry.

        Args:
            tempo_worklog_id: Tempo worklog ID
            solidtime_entry_id: Solidtime time entry ID
            issue_key: Jira issue key for reference
        """
        self.mappings[str(tempo_worklog_id)] = {
            "solidtime_entry_id": solidtime_entry_id,
            "issue_key": issue_key,
            "created_at": datetime.now().isoformat(),
        }
        self._save()
        logger.debug(f"Mapped Tempo {tempo_worklog_id} -> Solidtime {solidtime_entry_id}")

    def is_already_synced(self, tempo_worklog_id: str) -> bool:
        """Check if a Tempo worklog was already synced to Solidtime.

        Args:
            tempo_worklog_id: Tempo worklog ID

        Returns:
            True if already mapped, False otherwise
        """
        return str(tempo_worklog_id) in self.mappings

    def get_stats(self) -> dict[str, Any]:
        """Get mapping statistics.

        Returns:
            Dictionary with mapping counts
        """
        return {
            "total_mappings": len(self.mappings),
            "unique_issues": len({m.get("issue_key") for m in self.mappings.values()}),
        }

    def mark_processed(self, tempo_worklog_id: str) -> None:
        """Mark a mapping as processed in current sync.

        Args:
            tempo_worklog_id: Tempo worklog ID
        """
        if str(tempo_worklog_id) in self.mappings:
            self.mappings[str(tempo_worklog_id)]["processed"] = True

    def reset_processed(self) -> None:
        """Reset processed flag for all mappings (call at start of sync)."""
        for mapping in self.mappings.values():
            mapping["processed"] = False

    def get_unprocessed_mappings(self) -> list[tuple[str, dict[str, Any]]]:
        """Get mappings that were not processed (deleted worklogs).

        Returns:
            List of (tempo_worklog_id, mapping) tuples for unprocessed entries
        """
        return [
            (tempo_id, mapping)
            for tempo_id, mapping in self.mappings.items()
            if not mapping.get("processed", False)
        ]

    def remove_mapping(self, tempo_worklog_id: str) -> None:
        """Remove a mapping.

        Args:
            tempo_worklog_id: Tempo worklog ID
        """
        if str(tempo_worklog_id) in self.mappings:
            del self.mappings[str(tempo_worklog_id)]
            self._save()
            logger.debug(f"Removed mapping for Tempo {tempo_worklog_id}")
