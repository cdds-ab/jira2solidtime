#!/usr/bin/env python3
"""Main entrypoint for jira2solidtime daemon."""

import logging
import signal
import sys
from pathlib import Path

from jira2solidtime.config import Config
from jira2solidtime.daemon import SyncDaemon
from jira2solidtime.web.app import create_app

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point."""
    logger.info("Starting jira2solidtime...")

    # Load configuration
    config_path = Path("config.json")
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)

    try:
        config = Config(str(config_path))
        is_valid, errors = config.validate()
        if not is_valid:
            logger.error("Configuration validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Create daemon
    daemon = SyncDaemon(config)

    # Start daemon
    daemon.start()

    # Create and start web app
    app = create_app(config, daemon)
    port = config.web.get("port", 8080)

    logger.info(f"Starting web UI on port {port}...")

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame) -> None:  # type: ignore
        """Handle shutdown signals.

        Args:
            signum: Signal number
            frame: Stack frame
        """
        logger.info("Shutdown signal received, stopping daemon...")
        daemon.stop()
        logger.info("Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run web app
    try:
        app.run(
            host="0.0.0.0",  # nosec S104 - intended for Docker container
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True,
        )
    except Exception as e:
        logger.error(f"Failed to start web service: {e}")
        daemon.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
