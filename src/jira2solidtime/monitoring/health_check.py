"""Health check implementation for API services."""

import logging
from typing import Dict, Tuple

from ..api.tempo_client import TempoClient
from ..api.solidtime_client import SolidtimeClient

logger = logging.getLogger(__name__)


class HealthChecker:
    """Health check for external API dependencies."""

    def __init__(self, tempo_client: TempoClient, solidtime_client: SolidtimeClient):
        self.tempo_client = tempo_client
        self.solidtime_client = solidtime_client

    def check_tempo_health(self) -> Tuple[bool, str]:
        """Check Tempo API health."""
        try:
            if self.tempo_client.test_connection():
                return True, "OK"
            else:
                return False, "Connection test failed"
        except Exception as e:
            logger.error(f"Tempo health check failed: {e}")
            return False, str(e)

    def check_solidtime_health(self) -> Tuple[bool, str]:
        """Check Solidtime API health."""
        try:
            if self.solidtime_client.test_connection():
                return True, "OK"
            else:
                return False, "Connection test failed"
        except Exception as e:
            logger.error(f"Solidtime health check failed: {e}")
            return False, str(e)

    def check_all(self) -> Dict[str, Dict[str, str]]:
        """Perform all health checks and return status."""
        tempo_healthy, tempo_msg = self.check_tempo_health()
        solidtime_healthy, solidtime_msg = self.check_solidtime_health()

        return {
            "tempo": {
                "status": "healthy" if tempo_healthy else "unhealthy",
                "message": tempo_msg,
            },
            "solidtime": {
                "status": "healthy" if solidtime_healthy else "unhealthy",
                "message": solidtime_msg,
            },
            "overall": {
                "status": (
                    "healthy" if tempo_healthy and solidtime_healthy else "unhealthy"
                ),
                "message": (
                    "All services healthy"
                    if tempo_healthy and solidtime_healthy
                    else "One or more services unhealthy"
                ),
            },
        }
