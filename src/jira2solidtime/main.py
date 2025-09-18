#!/usr/bin/env python3
"""
Simplified jira2solidtime CLI with modern interface
"""

import click
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union

from .config import load_config
from .factories.client_factory import ClientFactory
from .services.sync_service import SyncService
from .domain.models import SyncRequest
from .mapping.field_mapper import FieldMapper
from .utils.worklog_mapping import WorklogMapping
from .utils.date_parser import parse_date_range
from .utils.logging import StructuredLogger, setup_console_logging
from .cli.progress import ModernCLI
from .monitoring.metrics_exporter import MetricsExporter
from . import __version__


def validate_configuration(config) -> list:
    """Validate configuration and return list of errors."""
    errors = []

    # Check required API tokens
    if not config.jira.tempo_api_token:
        errors.append("TEMPO_API_TOKEN missing in .env file")
    if not config.solidtime.api_token:
        errors.append("SOLIDTIME_API_TOKEN missing in .env file")
    if not config.solidtime.organization_id:
        errors.append("SOLIDTIME_ORGANIZATION_ID missing in .env file")

    # Check base URLs
    if not config.jira.base_url:
        errors.append("JIRA_BASE_URL missing in .env file")
    if not config.solidtime.base_url:
        errors.append("SOLIDTIME_BASE_URL missing in .env file")

    # Check mapping rules file
    mapping_file = Path("config/mapping_rules.yaml")
    if not mapping_file.exists():
        errors.append("config/mapping_rules.yaml not found")

    return errors


def test_api_connections(config) -> Dict[str, Dict[str, Union[bool, str]]]:
    """Test API connections and return results."""
    results: Dict[str, Dict[str, Union[bool, str]]] = {}

    # Test Tempo API
    try:
        tempo_client = ClientFactory.create_tempo_client(config)
        if tempo_client.test_connection():
            results["Tempo"] = {"success": True}
        else:
            results["Tempo"] = {"success": False, "error": "Connection failed"}
    except Exception as e:
        results["Tempo"] = {"success": False, "error": str(e)}

    # Test Solidtime API
    try:
        solidtime_client = ClientFactory.create_solidtime_client(config)
        if solidtime_client.test_connection():
            results["Solidtime"] = {"success": True}
        else:
            results["Solidtime"] = {"success": False, "error": "Connection failed"}
    except Exception as e:
        results["Solidtime"] = {"success": False, "error": str(e)}

    return results


def calculate_default_time_range() -> Tuple[datetime, datetime]:
    """Calculate default time range (current month)."""
    now = datetime.now()
    start_date = datetime(now.year, now.month, 1)

    # Calculate last day of current month
    if now.month == 12:
        end_date = datetime(now.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(now.year, now.month + 1, 1) - timedelta(days=1)

    return start_date, end_date


def perform_sync(
    config,
    cli: ModernCLI,
    logger: StructuredLogger,
    start_date: datetime,
    end_date: datetime,
    project_keys: Optional[list] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Perform the actual synchronization using the refactored service layer."""

    # Create sync request
    request = SyncRequest(
        start_date=start_date,
        end_date=end_date,
        project_keys=project_keys,
        dry_run=dry_run,
    )

    # Initialize clients using factory
    tempo_client = ClientFactory.create_tempo_client(config)
    jira_client = ClientFactory.create_jira_client(config)
    solidtime_client = ClientFactory.create_solidtime_client(config)

    # Initialize other dependencies
    field_mapper = FieldMapper(config.mapping_rules)
    worklog_mapping = WorklogMapping(data_dir=config.sync.data_dir)

    # Initialize metrics exporter if metrics directory is available
    metrics_exporter = None
    metrics_dir = os.getenv("METRICS_DIR", "/metrics")
    if os.path.exists(metrics_dir) or os.getenv("METRICS_DIR"):
        metrics_exporter = MetricsExporter(metrics_dir)

    # Create sync service
    sync_service = SyncService(
        tempo_client=tempo_client,
        jira_client=jira_client,
        solidtime_client=solidtime_client,
        field_mapper=field_mapper,
        worklog_mapping=worklog_mapping,
        logger=logger,
        metrics_exporter=metrics_exporter,
    )

    # Execute sync and return result as dictionary for backward compatibility
    result = sync_service.sync_worklogs(request, cli, config.sync.filter_user_email)

    return {
        "total_entries": result.total_entries,
        "changes": result.changes,
        "created": result.created,
        "updated": result.updated,
        "deleted": result.deleted,
        "total_hours": result.total_hours,
        "worklog_details": result.worklog_details,
    }


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(debug):
    """jira2solidtime - Simple Tempo ↔ Solidtime synchronization."""
    if debug:
        setup_console_logging("DEBUG")


@cli.command()
@click.option("--month", help="Sync specific month (YYYY-MM)")
@click.option("--from", "from_date", help="Start date (YYYY-MM-DD)")
@click.option("--to", "to_date", help="End date (YYYY-MM-DD)")
@click.option("--projects", help="Filter by project keys (comma-separated)")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be synced without doing it"
)
def sync(month, from_date, to_date, projects, dry_run):
    """Synchronize worklogs from Tempo to Solidtime."""
    start_time = time.time()

    # Initialize CLI and config
    cli_interface = ModernCLI()
    cli_interface.show_banner()

    try:
        config = load_config()
    except Exception as e:
        cli_interface.show_error(f"Failed to load configuration: {e}")
        return

    # Initialize structured logger
    logger = StructuredLogger(config.sync)

    # Validate configuration
    config_errors = validate_configuration(config)
    if not cli_interface.validate_config(config_errors):
        logger.log_validation_error(config_errors)
        return

    # Test API connections
    api_results = test_api_connections(config)
    if not cli_interface.validate_apis(api_results):
        for service, result in api_results.items():
            if not result["success"]:
                logger.log_api_error(service, result["error"])
        return

    # Parse time range
    if month:
        # Parse month format YYYY-MM
        try:
            year, month_num = month.split("-")
            start_date = datetime(int(year), int(month_num), 1)
            if int(month_num) == 12:
                end_date = datetime(int(year) + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(int(year), int(month_num) + 1, 1) - timedelta(
                    days=1
                )
        except (ValueError, IndexError):
            cli_interface.show_error("Invalid month format. Use YYYY-MM")
            return
    elif from_date and to_date:
        # Parse explicit date range
        try:
            start_date = datetime.strptime(from_date, "%Y-%m-%d")
            end_date = datetime.strptime(to_date, "%Y-%m-%d")
        except ValueError:
            cli_interface.show_error("Invalid date format. Use YYYY-MM-DD")
            return
    elif from_date:
        # Parse from_date only - could be range string
        try:
            start_date, end_date = parse_date_range(from_date)
        except Exception:
            cli_interface.show_error("Invalid date format")
            return
    else:
        # Default to current month
        start_date, end_date = calculate_default_time_range()

    # Parse project keys
    project_keys = (
        [key.strip() for key in projects.split(",") if key.strip()]
        if projects
        else config.sync.filter_project_keys
    )

    # Format time range for display
    time_range_display = cli_interface.format_time_range(
        start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
    )

    # Log sync start
    logger.log_sync_start(
        {"from": start_date.strftime("%Y-%m-%d"), "to": end_date.strftime("%Y-%m-%d")},
        project_keys,
        dry_run,
    )

    # Start sync
    cli_interface.start_sync(time_range_display, dry_run)

    try:
        # Perform sync
        results = perform_sync(
            config, cli_interface, logger, start_date, end_date, project_keys, dry_run
        )

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Show completion
        cli_interface.complete_sync(time_range_display, results, dry_run, project_keys)

        # Log completion
        logger.log_sync_complete(
            duration_ms,
            {
                "from": start_date.strftime("%Y-%m-%d"),
                "to": end_date.strftime("%Y-%m-%d"),
            },
            results,
            "success",
        )

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        cli_interface.show_error(str(e))

        logger.log_sync_complete(
            duration_ms,
            {
                "from": start_date.strftime("%Y-%m-%d"),
                "to": end_date.strftime("%Y-%m-%d"),
            },
            {"total_entries": 0, "changes": 0, "total_hours": 0.0},
            "error",
            str(e),
        )


@cli.command(name="health-check")
def health_check():
    """Check health of external API services."""
    try:
        config = load_config()
    except Exception as e:
        click.echo(f"Failed to load configuration: {e}", err=True)
        exit(1)

    # Initialize clients
    tempo_client = ClientFactory.create_tempo_client(config)
    solidtime_client = ClientFactory.create_solidtime_client(config)

    # Initialize metrics exporter if available
    metrics_exporter = None
    metrics_dir = os.getenv("METRICS_DIR", "/metrics")
    if os.path.exists(metrics_dir) or os.getenv("METRICS_DIR"):
        metrics_exporter = MetricsExporter(metrics_dir)

    # Create temporary sync service for health check
    from .utils.logging import StructuredLogger

    logger = StructuredLogger(config.sync)

    sync_service = SyncService(
        tempo_client=tempo_client,
        jira_client=None,  # Not needed for health check
        solidtime_client=solidtime_client,
        field_mapper=None,  # Not needed for health check
        worklog_mapping=None,  # Not needed for health check
        logger=logger,
        metrics_exporter=metrics_exporter,
    )

    # Perform health check
    health_status = sync_service.health_check()

    # Output results
    if health_status["overall"]["status"] == "healthy":
        click.echo("✅ All services healthy")
        exit(0)
    else:
        click.echo("❌ Health check failed:")
        for service, status in health_status.items():
            if service != "overall":
                icon = "✅" if status["status"] == "healthy" else "❌"
                click.echo(f"  {icon} {service.title()}: {status['message']}")
        exit(1)


@cli.command()
def version():
    """Show version information."""
    click.echo(f"jira2solidtime {__version__}")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
