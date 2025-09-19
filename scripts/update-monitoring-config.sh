#!/bin/bash

# Update monitoring configuration from jira2solidtime config service
# This script fetches configuration from the web API and updates files

set -e

CONFIG_SERVICE_URL=${CONFIG_SERVICE_URL:-"http://localhost:8080"}
MONITORING_DIR=${MONITORING_DIR:-"./monitoring"}

echo "🔄 Updating monitoring configuration from ${CONFIG_SERVICE_URL}"

# Wait for config service to be available
echo "⏳ Waiting for config service to be available..."
timeout 30s bash -c 'until curl -f ${CONFIG_SERVICE_URL}/api/status >/dev/null 2>&1; do sleep 1; done' || {
    echo "❌ Config service not available after 30 seconds"
    exit 1
}

echo "✅ Config service is available"

# Update Prometheus alert rules
echo "📊 Updating Prometheus alert rules..."
curl -f "${CONFIG_SERVICE_URL}/api/prometheus/alerts" > "${MONITORING_DIR}/prometheus/alert_rules.yml.new"
if [ $? -eq 0 ]; then
    mv "${MONITORING_DIR}/prometheus/alert_rules.yml.new" "${MONITORING_DIR}/prometheus/alert_rules.yml"
    echo "✅ Alert rules updated"
else
    echo "❌ Failed to update alert rules"
    rm -f "${MONITORING_DIR}/prometheus/alert_rules.yml.new"
    exit 1
fi

# Reload Prometheus configuration if it's running
if curl -f -X POST "http://localhost:9090/-/reload" >/dev/null 2>&1; then
    echo "🔄 Prometheus configuration reloaded"
else
    echo "ℹ️  Prometheus reload failed or not running (this is normal during startup)"
fi

echo "✅ Monitoring configuration update complete"