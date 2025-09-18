"""Domain models and value objects for sync operations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any


@dataclass(frozen=True)
class SyncRequest:
    """Request object for sync operations."""

    start_date: datetime
    end_date: datetime
    project_keys: Optional[List[str]] = None
    dry_run: bool = False


@dataclass(frozen=True)
class SyncResult:
    """Result object containing sync operation statistics."""

    total_entries: int
    changes: int
    created: int
    updated: int
    deleted: int
    total_hours: float
    worklog_details: Dict[str, List[Dict[str, Any]]]

    @classmethod
    def empty(cls) -> "SyncResult":
        """Create empty result for no-operation cases."""
        return cls(
            total_entries=0,
            changes=0,
            created=0,
            updated=0,
            deleted=0,
            total_hours=0.0,
            worklog_details={"created": [], "updated": [], "deleted": []},
        )
