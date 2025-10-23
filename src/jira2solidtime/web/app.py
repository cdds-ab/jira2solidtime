"""Flask web application for configuration and history."""

import json
import logging
from typing import Any

from flask import Flask, jsonify, render_template, request

from jira2solidtime.config import Config
from jira2solidtime.daemon import SyncDaemon
from jira2solidtime.history import History

logger = logging.getLogger(__name__)


def create_app(config: Config, daemon: SyncDaemon) -> Flask:
    """Create Flask application.

    Args:
        config: Application configuration
        daemon: Sync daemon instance

    Returns:
        Flask application
    """
    app = Flask(__name__, template_folder="templates")
    app.config["CONFIG"] = config
    app.config["DAEMON"] = daemon
    app.config["HISTORY"] = History()

    @app.route("/")
    def index() -> str:
        """Render main page.

        Returns:
            HTML page
        """
        config_data = config.to_dict()
        last_syncs = app.config["HISTORY"].get_last_syncs(10)
        stats = app.config["HISTORY"].get_sync_stats()

        return render_template(
            "index.html",
            config=config_data,
            last_syncs=last_syncs,
            stats=stats,
        )

    @app.route("/api/config", methods=["GET"])
    def get_config() -> Any:
        """Get current configuration.

        Returns:
            Configuration as JSON
        """
        return jsonify(app.config["CONFIG"].to_dict())

    @app.route("/api/config", methods=["POST"])
    def update_config() -> Any:
        """Update configuration.

        Returns:
            Status response
        """
        try:
            data = request.get_json()
            # Write to config.json
            with open("config.json", "w") as f:
                json.dump(data, f, indent=2)
            logger.info("Configuration updated via web UI")
            return jsonify({"success": True, "message": "Configuration saved"})
        except Exception as e:
            logger.error(f"Failed to update config: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/sync", methods=["POST"])
    def trigger_sync() -> Any:
        """Trigger immediate synchronization.

        Returns:
            Sync result
        """
        try:
            result = app.config["DAEMON"].sync_now()
            return jsonify(result)
        except Exception as e:
            logger.error(f"Manual sync failed: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/history", methods=["GET"])
    def get_history() -> Any:
        """Get sync history.

        Returns:
            List of sync records
        """
        limit = request.args.get("limit", 50, type=int)
        syncs = app.config["HISTORY"].get_last_syncs(limit)
        return jsonify({"syncs": syncs})

    @app.route("/api/stats", methods=["GET"])
    def get_stats() -> Any:
        """Get sync statistics.

        Returns:
            Statistics
        """
        stats = app.config["HISTORY"].get_sync_stats()
        return jsonify(stats)

    @app.errorhandler(404)
    def not_found(error: Exception) -> Any:
        """Handle 404 errors.

        Args:
            error: Exception

        Returns:
            Error response
        """
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def internal_error(error: Exception) -> Any:
        """Handle 500 errors.

        Args:
            error: Exception

        Returns:
            Error response
        """
        logger.error(f"Internal server error: {error}")
        return jsonify({"error": "Internal server error"}), 500

    return app
