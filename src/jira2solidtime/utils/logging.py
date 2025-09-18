"""Structured logging setup for machine-readable logs."""

import json
import logging
import structlog
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from ..config import SyncConfig


class StructuredLogger:
    """Handles structured JSON logging for sync operations."""

    def __init__(self, config: SyncConfig):
        self.config = config
        self.log_dir = Path(config.log_dir)
        self.log_file = self.log_dir / "sync.jsonl"

        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="ISO"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        self.logger = structlog.get_logger()

    def log_sync_start(
        self,
        time_range: Dict[str, str],
        projects: Optional[list] = None,
        dry_run: bool = False,
    ) -> None:
        """Log sync operation start."""
        self.logger.info(
            "sync_started",
            operation="sync",
            time_range=time_range,
            projects=projects or [],
            dry_run=dry_run,
            timestamp=datetime.now().isoformat(),
        )

    def log_sync_complete(
        self,
        duration_ms: int,
        time_range: Dict[str, str],
        results: Dict[str, Any],
        status: str = "success",
        error: Optional[str] = None,
    ) -> None:
        """Log sync operation completion."""
        log_entry = {
            "operation": "sync",
            "status": status,
            "duration_ms": duration_ms,
            "time_range": time_range,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

        if error:
            log_entry["error"] = error

        self.logger.info("sync_completed", **log_entry)

        # Also write to file in JSONL format for easy parsing
        self._write_to_file(log_entry)

    def log_validation_error(self, errors: list) -> None:
        """Log configuration validation errors."""
        self.logger.error(
            "validation_failed",
            operation="validation",
            errors=errors,
            timestamp=datetime.now().isoformat(),
        )

    def log_api_error(self, service: str, error: str) -> None:
        """Log API connectivity errors."""
        self.logger.error(
            "api_error",
            operation="connectivity_check",
            service=service,
            error=error,
            timestamp=datetime.now().isoformat(),
        )

    def _write_to_file(self, log_entry: Dict[str, Any]) -> None:
        """Write log entry to JSONL file."""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            # Don't fail sync operation due to logging issues
            logging.getLogger(__name__).warning(f"Failed to write to log file: {e}")


def setup_console_logging(level: str) -> None:
    """Setup basic console logging for development."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
