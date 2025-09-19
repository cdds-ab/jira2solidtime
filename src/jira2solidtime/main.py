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

from .config import load_config, get_config_manager
from .factories.client_factory import ClientFactory
from .services.sync_service import SyncService
from .domain.models import SyncRequest
from .mapping.field_mapper import FieldMapper
from .utils.worklog_mapping import WorklogMapping
from .utils.date_parser import parse_date_range
from .utils.logging import StructuredLogger, setup_console_logging
from .cli.progress import ModernCLI
from .monitoring.metrics_exporter import MetricsExporter
from .web.service import WebService
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


@cli.group()
def config():
    """Configuration management commands."""
    pass


@config.command("init")
@click.option(
    "--interactive", "-i", is_flag=True, help="Interactive configuration setup"
)
def config_init(interactive):
    """Initialize configuration database."""
    config_manager = get_config_manager()

    if interactive:
        click.echo("🔧 jira2solidtime Configuration Setup")
        click.echo("=====================================")

        # Jira configuration
        click.echo("\n📋 Jira Configuration:")
        jira_base_url = click.prompt(
            "Jira Base URL", default=config_manager.get_config("jira.base_url", "")
        )
        jira_user_email = click.prompt(
            "Jira User Email", default=config_manager.get_config("jira.user_email", "")
        )
        jira_api_token = click.prompt("Jira API Token", hide_input=True, default="")

        # Tempo configuration
        click.echo("\n⏱️  Tempo Configuration:")
        tempo_api_token = click.prompt("Tempo API Token", hide_input=True, default="")

        # Solidtime configuration
        click.echo("\n🎯 Solidtime Configuration:")
        solidtime_base_url = click.prompt(
            "Solidtime Base URL",
            default=config_manager.get_config("solidtime.base_url", ""),
        )
        solidtime_api_token = click.prompt(
            "Solidtime API Token", hide_input=True, default=""
        )
        solidtime_org_id = click.prompt(
            "Solidtime Organization ID",
            default=config_manager.get_config("solidtime.organization_id", ""),
        )

        # Sync configuration
        click.echo("\n🔄 Sync Configuration:")
        sync_schedule = click.prompt(
            "Sync Schedule (cron format)",
            default=config_manager.get_config("sync.schedule", "0 */10 6-22 * * *"),
        )
        dry_run = click.confirm(
            "Enable dry-run mode by default?",
            default=config_manager.get_config("sync.dry_run", True),
        )

        # Save configuration
        if jira_base_url:
            config_manager.set_config("jira.base_url", jira_base_url, "jira")
        if jira_user_email:
            config_manager.set_config("jira.user_email", jira_user_email, "jira")
        if jira_api_token:
            config_manager.set_config("jira.api_token", jira_api_token, "jira")
        if tempo_api_token:
            config_manager.set_config("jira.tempo_api_token", tempo_api_token, "jira")
        if solidtime_base_url:
            config_manager.set_config(
                "solidtime.base_url", solidtime_base_url, "solidtime"
            )
        if solidtime_api_token:
            config_manager.set_config(
                "solidtime.api_token", solidtime_api_token, "solidtime"
            )
        if solidtime_org_id:
            config_manager.set_config(
                "solidtime.organization_id", solidtime_org_id, "solidtime"
            )

        config_manager.set_config("sync.schedule", sync_schedule, "sync")
        config_manager.set_config("sync.dry_run", dry_run, "sync")

        click.echo("\n✅ Configuration saved to database")
    else:
        click.echo("✅ Configuration database initialized")
        click.echo(
            "Run 'jira2solidtime config init --interactive' for interactive setup"
        )


@config.command("get")
@click.argument("key")
def config_get(key):
    """Get configuration value."""
    config_manager = get_config_manager()
    value = config_manager.get_config(key)

    if value is None:
        click.echo(f"Configuration key '{key}' not found", err=True)
        exit(1)

    if isinstance(value, str) and any(
        secret in key.lower() for secret in ["token", "password", "secret"]
    ):
        click.echo("*" * len(str(value)))  # Hide sensitive values
    else:
        click.echo(value)


@config.command("set")
@click.argument("key")
@click.argument("value")
@click.option("--category", help="Configuration category")
def config_set(key, value, category):
    """Set configuration value."""
    config_manager = get_config_manager()

    # Auto-convert boolean strings
    if value.lower() in ("true", "false"):
        value = value.lower() == "true"

    # Auto-convert numeric strings
    try:
        if "." in value:
            value = float(value)
        else:
            value = int(value)
    except ValueError:
        pass  # Keep as string

    config_manager.set_config(key, value, category)
    click.echo(f"✅ Set {key} = {value}")


@config.command("list")
@click.option("--category", help="Filter by category")
@click.option(
    "--hide-secrets", is_flag=True, default=True, help="Hide sensitive values"
)
def config_list(category, hide_secrets):
    """List configuration entries."""
    config_manager = get_config_manager()
    config_dict = config_manager.list_config(category)

    if not config_dict:
        click.echo("No configuration entries found")
        return

    for key, value in sorted(config_dict.items()):
        if hide_secrets and any(
            secret in key.lower() for secret in ["token", "password", "secret"]
        ):
            display_value = "*" * 8
        else:
            display_value = str(value)

        click.echo(f"{key} = {display_value}")


@config.command("delete")
@click.argument("key")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def config_delete(key, confirm):
    """Delete configuration entry."""
    config_manager = get_config_manager()

    if not confirm:
        if not click.confirm(f"Delete configuration key '{key}'?"):
            click.echo("Cancelled")
            return

    if config_manager.db.delete_config(key):
        click.echo(f"✅ Deleted {key}")
    else:
        click.echo(f"Configuration key '{key}' not found", err=True)
        exit(1)


@config.command("export")
@click.option("--output", "-o", help="Output file path")
def config_export(output):
    """Export configuration to JSON file."""
    import json

    config_manager = get_config_manager()
    config_data = config_manager.export_config()

    if output:
        with open(output, "w") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        click.echo(f"✅ Configuration exported to {output}")
    else:
        click.echo(json.dumps(config_data, indent=2, ensure_ascii=False))


@config.command("import")
@click.argument("input_file")
@click.option("--overwrite", is_flag=True, help="Overwrite existing entries")
def config_import(input_file, overwrite):
    """Import configuration from JSON file."""
    import json

    try:
        with open(input_file, "r") as f:
            config_data = json.load(f)
    except FileNotFoundError:
        click.echo(f"File '{input_file}' not found", err=True)
        exit(1)
    except json.JSONDecodeError as e:
        click.echo(f"Invalid JSON file: {e}", err=True)
        exit(1)

    config_manager = get_config_manager()
    config_manager.import_config(config_data, overwrite=overwrite)

    if overwrite:
        click.echo("✅ Configuration imported with overwrite")
    else:
        click.echo("✅ Configuration imported (existing entries preserved)")


@config.command("validate")
def config_validate():
    """Validate current configuration and test API connections."""
    try:
        config = load_config()
    except Exception as e:
        click.echo(f"❌ Failed to load configuration: {e}", err=True)
        exit(1)

    # Validate configuration
    config_errors = validate_configuration(config)

    if config_errors:
        click.echo("❌ Configuration validation failed:")
        for error in config_errors:
            click.echo(f"  - {error}")
        exit(1)

    # Test API connections
    click.echo("🔗 Testing API connections...")
    api_results = test_api_connections(config)

    all_success = True
    for service, result in api_results.items():
        if result["success"]:
            click.echo(f"  ✅ {service}: Connected")
        else:
            click.echo(f"  ❌ {service}: {result['error']}")
            all_success = False

    if all_success:
        click.echo("✅ Configuration is valid and all APIs are accessible")
    else:
        click.echo("❌ Some API connections failed")
        exit(1)


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")  # nosec B104
@click.option("--port", default=8080, help="Port to bind to")
def serve(host, port):
    """Start web service mode with admin dashboard."""
    click.echo("🌐 Starting jira2solidtime admin dashboard...")

    try:
        # Verify configuration exists
        load_config()  # Just verify it loads
        click.echo("✅ Configuration loaded successfully")

        # Start web service
        web_service = WebService(host=host, port=port)
        web_service.run()

    except KeyboardInterrupt:
        click.echo("\n🛑 Shutting down web service...")
    except Exception as e:
        click.echo(f"❌ Failed to start web service: {e}", err=True)
        exit(1)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
