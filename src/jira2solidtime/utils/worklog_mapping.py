"""Worklog ID mapping system for tracking Tempo->Solidtime relationships."""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Set, List
from datetime import datetime

logger = logging.getLogger(__name__)


class WorklogMapping:
    """Manages mapping between Tempo worklog IDs and Solidtime entry IDs."""

    def __init__(
        self, mapping_file: str = "worklog_mapping.json", data_dir: str = "./data"
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.mapping_file = self.data_dir / mapping_file
        self.mappings: Dict[str, Dict] = {}
        self.load_mappings()

    def load_mappings(self) -> None:
        """Load existing mappings from file."""
        if self.mapping_file.exists():
            try:
                with open(self.mapping_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.mappings = data.get("mappings", {})

                    # Ensure backward compatibility - add needs_update flag to old mappings
                    for mapping in self.mappings.values():
                        if "needs_update" not in mapping:
                            mapping["needs_update"] = False

                    logger.debug(f"Loaded {len(self.mappings)} worklog mappings")
            except json.JSONDecodeError as e:
                logger.warning(f"Mapping file is corrupted, creating new one: {e}")
                self.mappings = {}
                # Save a fresh empty mappings file
                self.save_mappings()
            except OSError as e:
                logger.warning(f"Could not read mappings file: {e}")
                self.mappings = {}
        else:
            logger.info("Creating new worklog mapping file")
            self.mappings = {}
            # Create initial empty mapping file
            self.save_mappings()

    def save_mappings(self) -> None:
        """Save mappings to file."""
        try:
            data = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "mappings": self.mappings,
            }
            with open(self.mapping_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.mappings)} worklog mappings")
        except OSError as e:
            logger.error(f"Failed to save mappings file: {e}")

    def add_mapping(
        self,
        tempo_worklog_id: str,
        solidtime_entry_id: str,
        issue_key: str,
        tempo_updated_at: str,
        solidtime_updated_at: Optional[str] = None,
        needs_update: bool = False,
    ) -> None:
        """Add a mapping between Tempo worklog and Solidtime entry."""
        self.mappings[tempo_worklog_id] = {
            "solidtime_entry_id": solidtime_entry_id,
            "issue_key": issue_key,
            "tempo_updated_at": tempo_updated_at,
            "solidtime_updated_at": solidtime_updated_at,
            "needs_update": needs_update,
            "created_at": datetime.now().isoformat(),
        }
        logger.debug(
            f"Added mapping: Tempo {tempo_worklog_id} -> Solidtime {solidtime_entry_id} (needs_update: {needs_update})"
        )

    def get_solidtime_entry_id(self, tempo_worklog_id: str) -> Optional[str]:
        """Get the Solidtime entry ID for a given Tempo worklog ID."""
        mapping = self.mappings.get(tempo_worklog_id)
        return mapping["solidtime_entry_id"] if mapping else None

    def get_tempo_worklog_id(self, solidtime_entry_id: str) -> Optional[str]:
        """Get the Tempo worklog ID for a given Solidtime entry ID."""
        for tempo_id, mapping in self.mappings.items():
            if mapping["solidtime_entry_id"] == solidtime_entry_id:
                return tempo_id
        return None

    def remove_mapping(self, tempo_worklog_id: str) -> None:
        """Remove a mapping by Tempo worklog ID."""
        if tempo_worklog_id in self.mappings:
            del self.mappings[tempo_worklog_id]
            logger.debug(f"Removed mapping for Tempo worklog {tempo_worklog_id}")

    def get_mapped_solidtime_entry_ids(self) -> Set[str]:
        """Get all Solidtime entry IDs that are currently mapped."""
        return {mapping["solidtime_entry_id"] for mapping in self.mappings.values()}

    def get_mapped_tempo_worklog_ids(self) -> Set[str]:
        """Get all Tempo worklog IDs that are currently mapped."""
        return set(self.mappings.keys())

    def mark_for_update(self, tempo_worklog_id: str) -> None:
        """Mark a mapping as needing update."""
        if tempo_worklog_id in self.mappings:
            self.mappings[tempo_worklog_id]["needs_update"] = True
            logger.debug(f"Marked Tempo worklog {tempo_worklog_id} for update")

    def clear_update_flag(self, tempo_worklog_id: str) -> None:
        """Clear the needs_update flag after successful update."""
        if tempo_worklog_id in self.mappings:
            self.mappings[tempo_worklog_id]["needs_update"] = False
            logger.debug(f"Cleared update flag for Tempo worklog {tempo_worklog_id}")

    def needs_update(self, tempo_worklog_id: str) -> bool:
        """Check if a mapping is marked for update."""
        mapping = self.mappings.get(tempo_worklog_id)
        return mapping.get("needs_update", False) if mapping else False

    def get_entries_needing_update(self) -> List[str]:
        """Get all Tempo worklog IDs that need updating."""
        return [
            tempo_id
            for tempo_id, mapping in self.mappings.items()
            if mapping.get("needs_update", False)
        ]

    def is_tempo_worklog_newer(
        self, tempo_worklog_id: str, tempo_updated_at: str
    ) -> bool:
        """Check if a Tempo worklog has been updated since last sync."""
        mapping = self.mappings.get(tempo_worklog_id)
        if not mapping:
            return True  # New worklog

        try:
            stored_timestamp = mapping["tempo_updated_at"]
            # If stored timestamp is empty (from recovery), don't treat as newer
            if not stored_timestamp:
                return False  # Recovered mappings are assumed current
            # Compare timestamps (ISO format)
            return tempo_updated_at > stored_timestamp
        except (KeyError, TypeError):
            return True  # Assume newer if we can't compare

    def cleanup_orphaned_mappings(self, existing_tempo_ids: Set[str]) -> None:
        """Remove mappings for Tempo worklogs that no longer exist."""
        to_remove = []
        for tempo_id in self.mappings:
            if tempo_id not in existing_tempo_ids:
                to_remove.append(tempo_id)

        for tempo_id in to_remove:
            self.remove_mapping(tempo_id)

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} orphaned mappings")

    def get_statistics(self) -> Dict:
        """Get mapping statistics."""
        return {
            "total_mappings": len(self.mappings),
            "unique_issues": len(set(m["issue_key"] for m in self.mappings.values())),
            "oldest_mapping": min(
                (m["created_at"] for m in self.mappings.values()), default=None
            ),
            "newest_mapping": max(
                (m["created_at"] for m in self.mappings.values()), default=None
            ),
        }

    def recover_mappings_from_descriptions(self, solidtime_entries: List[Dict]) -> int:
        """Recover mappings from Solidtime entry descriptions containing [JiraSync:tempoWorklogId]."""
        import re

        recovered_count = 0

        for entry in solidtime_entries:
            description = entry.get("description", "")
            entry_id = entry.get("id")

            if not entry_id:
                continue

            # Look for [JiraSync:123] pattern
            match = re.search(r"\[JiraSync:(\d+)\]", description)
            if match:
                tempo_worklog_id = match.group(1)

                # Extract issue key from start of description
                issue_match = re.match(r"^([A-Z]+-\d+):", description)
                if issue_match:
                    issue_key = issue_match.group(1)

                    # Add recovered mapping
                    if tempo_worklog_id not in self.mappings:
                        self.mappings[tempo_worklog_id] = {
                            "solidtime_entry_id": entry_id,
                            "issue_key": issue_key,
                            "tempo_updated_at": "",  # Unknown
                            "solidtime_updated_at": entry.get("updated_at"),
                            "created_at": datetime.now().isoformat(),
                            "recovered": True,
                        }
                        recovered_count += 1
                        logger.info(
                            f"Recovered mapping: Tempo {tempo_worklog_id} -> Solidtime {entry_id}"
                        )

        if recovered_count > 0:
            self.save_mappings()
            logger.info(f"Recovered {recovered_count} mappings from entry descriptions")

        return recovered_count
