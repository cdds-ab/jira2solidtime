"""FastAPI web service for jira2solidtime configuration and monitoring."""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn

from ..config import get_config_manager, load_config
from ..factories.client_factory import ClientFactory


class WebService:
    """FastAPI web service for configuration management and monitoring."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):  # nosec B104
        """Initialize web service.

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        self.host = host
        self.port = port
        self.config_manager = get_config_manager()
        self.app = self._create_app()

    def _create_app(self) -> FastAPI:
        """Create FastAPI application with routes."""
        app = FastAPI(
            title="jira2solidtime Admin Dashboard",
            description="Configuration and monitoring interface for jira2solidtime",
            version="0.2.0",
        )

        # Static files and templates
        templates_dir = Path(__file__).parent / "templates"
        static_dir = Path(__file__).parent / "static"

        if templates_dir.exists():
            templates = Jinja2Templates(directory=str(templates_dir))

        if static_dir.exists():
            app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        # Routes
        @app.get("/", response_class=HTMLResponse)
        async def dashboard(request: Request):
            """Main dashboard page."""
            try:
                config = load_config()
                system_status = await self._get_system_status()

                if templates_dir.exists():
                    return templates.TemplateResponse(
                        "dashboard.html",
                        {
                            "request": request,
                            "config": config,
                            "system_status": system_status,
                        },
                    )
                else:
                    # Fallback simple HTML
                    return HTMLResponse(
                        content=self._generate_simple_dashboard(config, system_status)
                    )

            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to load dashboard: {str(e)}"
                )

        @app.get("/api/config")
        async def get_all_config():
            """Get all configuration entries."""
            try:
                return self.config_manager.list_config()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/config/{category}")
        async def get_config_by_category(category: str):
            """Get configuration entries by category."""
            try:
                return self.config_manager.list_config(category=category)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/config/key/{key}")
        async def get_config_value(key: str):
            """Get single configuration value."""
            try:
                value = self.config_manager.get_config(key)
                if value is None:
                    raise HTTPException(
                        status_code=404, detail=f"Configuration key '{key}' not found"
                    )
                return {"key": key, "value": value}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/api/config/{key}")
        async def set_config_value(key: str, data: Dict[str, Any]):
            """Set configuration value."""
            try:
                value = data.get("value")
                category = data.get("category")

                if value is None:
                    raise HTTPException(
                        status_code=400, detail="Missing 'value' in request"
                    )

                self.config_manager.set_config(key, value, category)
                return {"message": f"Configuration '{key}' updated successfully"}

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.delete("/api/config/{key}")
        async def delete_config_value(key: str):
            """Delete configuration entry."""
            try:
                if self.config_manager.db.delete_config(key):
                    return {"message": f"Configuration '{key}' deleted successfully"}
                else:
                    raise HTTPException(
                        status_code=404, detail=f"Configuration key '{key}' not found"
                    )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/config/export")
        async def export_config():
            """Export all configuration."""
            try:
                return self.config_manager.export_config()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/api/config/import")
        async def import_config(data: Dict[str, Any]):
            """Import configuration from backup."""
            try:
                overwrite = data.get("overwrite", False)
                config_data = data.get("config_data")

                if not config_data:
                    raise HTTPException(
                        status_code=400, detail="Missing 'config_data' in request"
                    )

                self.config_manager.import_config(config_data, overwrite=overwrite)
                return {"message": "Configuration imported successfully"}

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/status")
        async def system_status():
            """Get system status and health information."""
            try:
                return await self._get_system_status()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/api/test-connections")
        async def test_api_connections():
            """Test API connections."""
            try:
                config = load_config()
                results = {}

                # Test Tempo API
                try:
                    tempo_client = ClientFactory.create_tempo_client(config)
                    if tempo_client.test_connection():
                        results["tempo"] = {
                            "status": "success",
                            "message": "Connected successfully",
                        }
                    else:
                        results["tempo"] = {
                            "status": "error",
                            "message": "Connection failed",
                        }
                except Exception as e:
                    results["tempo"] = {"status": "error", "message": str(e)}

                # Test Solidtime API
                try:
                    solidtime_client = ClientFactory.create_solidtime_client(config)
                    if solidtime_client.test_connection():
                        results["solidtime"] = {
                            "status": "success",
                            "message": "Connected successfully",
                        }
                    else:
                        results["solidtime"] = {
                            "status": "error",
                            "message": "Connection failed",
                        }
                except Exception as e:
                    results["solidtime"] = {"status": "error", "message": str(e)}

                return results

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Configuration endpoints for other services
        @app.get("/api/prometheus/alerts")
        async def get_prometheus_alerts():
            """Generate Prometheus alert rules from configuration."""
            try:
                return await self._generate_prometheus_alerts()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/grafana/dashboards")
        async def get_grafana_dashboards():
            """Generate Grafana dashboard configuration."""
            try:
                return await self._generate_grafana_dashboard()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/docker/environment")
        async def get_docker_environment():
            """Generate environment variables for Docker containers."""
            try:
                config = load_config()
                env_vars = {
                    "SYNC_SCHEDULE": config.sync.schedule,
                    "HEALTH_CHECK_SCHEDULE": config.sync.health_check_schedule,
                    "SYNC_ALERT_THRESHOLD": str(
                        config.monitoring.alert_threshold_seconds
                    ),
                    "SYNC_START_HOUR": str(config.monitoring.sync_start_hour),
                    "SYNC_END_HOUR": str(config.monitoring.sync_end_hour),
                }
                return env_vars
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/api/backup/create")
        async def create_backup():
            """Create configuration backup."""
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_data = self.config_manager.export_config()

                # Save to file
                backup_dir = Path("./data/backups")
                backup_dir.mkdir(parents=True, exist_ok=True)
                backup_file = backup_dir / f"config_backup_{timestamp}.json"

                with open(backup_file, "w") as f:
                    json.dump(backup_data, f, indent=2, ensure_ascii=False)

                return {
                    "message": "Backup created successfully",
                    "backup_file": str(backup_file),
                    "timestamp": timestamp,
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/backup/list")
        async def list_backups():
            """List available backups."""
            try:
                backup_dir = Path("./data/backups")
                if not backup_dir.exists():
                    return {"backups": []}

                backups = []
                for backup_file in backup_dir.glob("config_backup_*.json"):
                    stat = backup_file.stat()
                    backups.append(
                        {
                            "filename": backup_file.name,
                            "size": stat.st_size,
                            "created": datetime.fromtimestamp(
                                stat.st_ctime
                            ).isoformat(),
                            "modified": datetime.fromtimestamp(
                                stat.st_mtime
                            ).isoformat(),
                        }
                    )

                # Sort by creation time, newest first
                backups.sort(key=lambda x: x["created"], reverse=True)
                return {"backups": backups}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/api/backup/restore/{backup_filename}")
        async def restore_backup(backup_filename: str, data: Dict[str, Any]):
            """Restore configuration from backup."""
            try:
                overwrite = data.get("overwrite", False)
                backup_dir = Path("./data/backups")
                backup_file = backup_dir / backup_filename

                if not backup_file.exists():
                    raise HTTPException(status_code=404, detail="Backup file not found")

                with open(backup_file, "r") as f:
                    backup_data = json.load(f)

                self.config_manager.import_config(backup_data, overwrite=overwrite)

                return {
                    "message": f"Configuration restored from {backup_filename}",
                    "overwrite": overwrite,
                }
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/api/reload/prometheus")
        async def reload_prometheus():
            """Trigger Prometheus configuration reload."""
            try:
                import requests

                # Generate new alert rules
                alert_rules = await self._generate_prometheus_alerts()

                # Write to monitoring directory
                alert_rules_file = Path("./monitoring/prometheus/alert_rules.yml")
                alert_rules_file.parent.mkdir(parents=True, exist_ok=True)

                with open(alert_rules_file, "w") as f:
                    f.write(alert_rules)

                # Try to reload Prometheus
                try:
                    response = requests.post(
                        "http://localhost:9090/-/reload", timeout=5
                    )
                    if response.status_code == 200:
                        return {
                            "message": "Prometheus configuration reloaded successfully"
                        }
                    else:
                        return {
                            "message": f"Alert rules updated, but Prometheus reload failed: {response.status_code}"
                        }
                except requests.RequestException:
                    return {
                        "message": "Alert rules updated, but Prometheus is not accessible"
                    }

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/api/reload/monitoring")
        async def reload_all_monitoring():
            """Trigger full monitoring stack configuration reload."""
            try:
                # Update alert rules
                await reload_prometheus()

                # Could add Grafana dashboard updates here
                # Could add Alertmanager config updates here

                return {"message": "Monitoring configuration reload triggered"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        return app

    async def _get_system_status(self) -> Dict[str, Any]:
        """Get system status information."""
        try:
            config = load_config()

            status = {
                "timestamp": datetime.now().isoformat(),
                "configuration": {
                    "jira_configured": bool(
                        config.jira.base_url and config.jira.api_token
                    ),
                    "tempo_configured": bool(config.jira.tempo_api_token),
                    "solidtime_configured": bool(
                        config.solidtime.base_url and config.solidtime.api_token
                    ),
                    "sync_schedule": config.sync.schedule,
                    "dry_run_mode": config.sync.dry_run,
                },
                "database": {
                    "config_entries": len(self.config_manager.list_config()),
                    "database_path": self.config_manager.db.db_path,
                },
                "directories": {
                    "data_dir": config.sync.data_dir,
                    "log_dir": config.sync.log_dir,
                    "data_dir_exists": os.path.exists(config.sync.data_dir),
                    "log_dir_exists": os.path.exists(config.sync.log_dir),
                },
            }

            return status

        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    async def _generate_prometheus_alerts(self) -> str:
        """Generate Prometheus alert rules YAML."""
        try:
            config = load_config()

            alert_rules = f"""groups:
  - name: jira2solidtime_alerts
    rules:
      - alert: SyncFailed
        expr: jira2solidtime_sync_success == 0
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "jira2solidtime sync has failed"
          description: "The last sync operation failed and has been failing for more than 10 minutes."

      - alert: SlowSyncOperation
        expr: jira2solidtime_sync_duration_seconds > 15
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "jira2solidtime sync operation slower than usual"
          description: "Sync operation is taking {{{{ $value }}}} seconds, normal is 3-5 seconds."

      - alert: LongRunningSyncOperation
        expr: jira2solidtime_sync_duration_seconds > 30
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "jira2solidtime sync operation taking too long"
          description: "Sync operation is taking {{{{ $value }}}} seconds, which indicates a serious problem."

      - alert: APIServiceDown
        expr: jira2solidtime_tempo_api_healthy == 0 or jira2solidtime_solidtime_api_healthy == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "External API service is down"
          description: "One or more external API services (Tempo/Solidtime) are not responding."

      - alert: NoRecentSync
        expr: time() - jira2solidtime_last_sync_timestamp > {config.monitoring.alert_threshold_seconds} and hour() >= {config.monitoring.sync_start_hour} and hour() <= {config.monitoring.sync_end_hour}
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "No recent sync operation during business hours"
          description: "No sync operation has been performed in the last {config.monitoring.alert_threshold_seconds} seconds. Sync runs during configured business hours ({config.monitoring.sync_start_hour}:00 - {config.monitoring.sync_end_hour}:00), so this indicates a problem with the sync process."
"""

            return alert_rules

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to generate alerts: {str(e)}"
            )

    async def _generate_grafana_dashboard(self) -> Dict[str, Any]:
        """Generate Grafana dashboard JSON."""
        # This would contain a complete Grafana dashboard configuration
        # For now, returning a placeholder
        return {
            "dashboard": {
                "title": "jira2solidtime Monitoring",
                "tags": ["jira2solidtime"],
                "panels": [
                    {
                        "title": "Sync Success Rate",
                        "type": "stat",
                        "targets": [{"expr": "jira2solidtime_sync_success"}],
                    },
                    {
                        "title": "Sync Duration",
                        "type": "graph",
                        "targets": [{"expr": "jira2solidtime_sync_duration_seconds"}],
                    },
                ],
            }
        }

    def _generate_simple_dashboard(self, config, system_status) -> str:
        """Generate simple HTML dashboard when templates are not available."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>jira2solidtime Admin Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .success {{ background-color: #d4edda; border: 1px solid #c3e6cb; }}
        .error {{ background-color: #f8d7da; border: 1px solid #f5c6cb; }}
        .info {{ background-color: #d1ecf1; border: 1px solid #bee5eb; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>🔧 jira2solidtime Admin Dashboard</h1>

    <h2>System Status</h2>
    <div class="status {"success" if system_status.get("configuration", {}).get("jira_configured", False) else "error"}">
        <strong>Jira:</strong> {"✅ Configured" if system_status.get("configuration", {}).get("jira_configured", False) else "❌ Not Configured"}
    </div>
    <div class="status {"success" if system_status.get("configuration", {}).get("solidtime_configured", False) else "error"}">
        <strong>Solidtime:</strong> {"✅ Configured" if system_status.get("configuration", {}).get("solidtime_configured", False) else "❌ Not Configured"}
    </div>
    <div class="status info">
        <strong>Sync Schedule:</strong> {system_status.get("configuration", {}).get("sync_schedule", "Not set")}
    </div>

    <h2>Configuration</h2>
    <p>Configuration entries: {system_status.get("database", {}).get("config_entries", 0)}</p>
    <p>Database: {system_status.get("database", {}).get("database_path", "Unknown")}</p>

    <h2>API Endpoints</h2>
    <ul>
        <li><a href="/api/config">GET /api/config</a> - List all configuration</li>
        <li><a href="/api/status">GET /api/status</a> - System status</li>
        <li><a href="/api/prometheus/alerts">GET /api/prometheus/alerts</a> - Prometheus alerts</li>
        <li>POST /api/test-connections - Test API connections</li>
    </ul>

    <h2>Links</h2>
    <ul>
        <li><a href="http://localhost:9090" target="_blank">Prometheus</a></li>
        <li><a href="http://localhost:3000" target="_blank">Grafana</a></li>
        <li><a href="http://localhost:9093" target="_blank">Alertmanager</a></li>
    </ul>
</body>
</html>
        """

    def run(self) -> None:
        """Run the web service."""
        print(
            f"🌐 Starting jira2solidtime admin dashboard on http://{self.host}:{self.port}"
        )
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")
