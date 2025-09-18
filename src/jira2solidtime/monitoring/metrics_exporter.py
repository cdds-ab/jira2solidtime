"""Prometheus metrics exporter for monitoring."""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from prometheus_client import CollectorRegistry, Gauge, Info, write_to_textfile

from ..domain.models import SyncResult


class MetricsExporter:
    """Export sync metrics to Prometheus format."""

    def __init__(self, metrics_dir: str = "/metrics"):
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(exist_ok=True)
        self.metrics_file = self.metrics_dir / "jira2solidtime.prom"

    def export_sync_metrics(
        self,
        result: SyncResult,
        duration_ms: int,
        status: str = "success",
        error: Optional[str] = None,
    ) -> None:
        """Export sync result metrics to Prometheus format."""
        registry = CollectorRegistry()

        # Sync performance metrics
        Gauge(
            "jira2solidtime_sync_duration_seconds",
            "Duration of sync operation in seconds",
            registry=registry,
        ).set(duration_ms / 1000.0)

        # Business metrics
        Gauge(
            "jira2solidtime_entries_total",
            "Total number of worklog entries processed",
            registry=registry,
        ).set(result.total_entries)

        Gauge(
            "jira2solidtime_changes_total",
            "Total number of changes made",
            registry=registry,
        ).set(result.changes)

        Gauge(
            "jira2solidtime_entries_created",
            "Number of entries created",
            registry=registry,
        ).set(result.created)

        Gauge(
            "jira2solidtime_entries_updated",
            "Number of entries updated",
            registry=registry,
        ).set(result.updated)

        Gauge(
            "jira2solidtime_entries_deleted",
            "Number of entries deleted",
            registry=registry,
        ).set(result.deleted)

        Gauge(
            "jira2solidtime_hours_total", "Total hours synced", registry=registry
        ).set(result.total_hours)

        # Status metrics
        Gauge(
            "jira2solidtime_last_sync_timestamp",
            "Timestamp of last sync operation",
            registry=registry,
        ).set(datetime.now().timestamp())

        Gauge(
            "jira2solidtime_sync_success",
            "Whether last sync was successful (1=success, 0=failure)",
            registry=registry,
        ).set(1 if status == "success" else 0)

        # Application info
        Info("jira2solidtime_build_info", "Build information", registry=registry).info(
            {
                "version": os.getenv("APP_VERSION", "0.1.0"),
                "status": status,
                "error": error or "",
            }
        )

        # Write metrics to file for Prometheus file discovery
        write_to_textfile(str(self.metrics_file), registry)

    def export_health_metrics(
        self, tempo_healthy: bool, solidtime_healthy: bool
    ) -> None:
        """Export health check metrics."""
        registry = CollectorRegistry()

        Gauge(
            "jira2solidtime_tempo_api_healthy",
            "Tempo API health status (1=healthy, 0=unhealthy)",
            registry=registry,
        ).set(1 if tempo_healthy else 0)

        Gauge(
            "jira2solidtime_solidtime_api_healthy",
            "Solidtime API health status (1=healthy, 0=unhealthy)",
            registry=registry,
        ).set(1 if solidtime_healthy else 0)

        Gauge(
            "jira2solidtime_overall_healthy",
            "Overall application health (1=healthy, 0=unhealthy)",
            registry=registry,
        ).set(1 if tempo_healthy and solidtime_healthy else 0)

        # Append health metrics to main file
        try:
            with open(self.metrics_file, "a") as f:
                f.write("\n")
                for metric in registry.collect():
                    for sample in metric.samples:
                        f.write(f"# HELP {sample.name} {metric.documentation}\n")
                        f.write(f"# TYPE {sample.name} {metric.type}\n")
                        f.write(f"{sample.name} {sample.value}\n")
        except Exception:
            # Fallback: write to separate file
            health_file = self.metrics_dir / "health.prom"
            write_to_textfile(str(health_file), registry)
