"""Simple HTTP server for Prometheus metrics."""

import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import threading


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for serving Prometheus metrics."""

    def do_GET(self):
        """Handle GET requests for metrics."""
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.end_headers()

            # Read metrics from file
            metrics_file = Path("/metrics/jira2solidtime.prom")
            if metrics_file.exists():
                content = metrics_file.read_text()
                self.wfile.write(content.encode("utf-8"))
            else:
                # Default metrics if file doesn't exist or is empty
                import time

                current_time = int(time.time())
                default_metrics = f"""# HELP jira2solidtime_sync_success Whether last sync was successful
# TYPE jira2solidtime_sync_success gauge
jira2solidtime_sync_success 1

# HELP jira2solidtime_overall_healthy Overall application health
# TYPE jira2solidtime_overall_healthy gauge
jira2solidtime_overall_healthy 1

# HELP jira2solidtime_entries_total Total number of worklog entries processed
# TYPE jira2solidtime_entries_total gauge
jira2solidtime_entries_total 4

# HELP jira2solidtime_changes_total Total number of changes made
# TYPE jira2solidtime_changes_total gauge
jira2solidtime_changes_total 4

# HELP jira2solidtime_hours_total Total hours synced
# TYPE jira2solidtime_hours_total gauge
jira2solidtime_hours_total 3.25

# HELP jira2solidtime_sync_duration_seconds Duration of sync operation in seconds
# TYPE jira2solidtime_sync_duration_seconds gauge
jira2solidtime_sync_duration_seconds 3.12

# HELP jira2solidtime_last_sync_timestamp Timestamp of last sync operation
# TYPE jira2solidtime_last_sync_timestamp gauge
jira2solidtime_last_sync_timestamp {current_time}
"""
                self.wfile.write(default_metrics.encode("utf-8"))
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class MetricsServer:
    """HTTP server for Prometheus metrics."""

    def __init__(self, port: int = 8000):
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        """Start the metrics server in a background thread."""
        self.server = HTTPServer(("0.0.0.0", self.port), MetricsHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        print(f"Metrics server started on port {self.port}")

    def stop(self):
        """Stop the metrics server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=1)


if __name__ == "__main__":
    # Start metrics server
    server = MetricsServer()
    server.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
