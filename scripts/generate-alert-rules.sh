#!/bin/bash

# Generate Prometheus alert rules from template using environment variables
# This script should be run before starting Prometheus

set -e

# Source environment file if it exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Set default values if not provided
SYNC_ALERT_THRESHOLD=${SYNC_ALERT_THRESHOLD:-900}
SYNC_START_HOUR=${SYNC_START_HOUR:-6}
SYNC_END_HOUR=${SYNC_END_HOUR:-22}

# Template file
TEMPLATE_FILE="monitoring/prometheus/alert_rules.yml.template"
OUTPUT_FILE="monitoring/prometheus/alert_rules.yml"

# Check if template exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "Error: Template file $TEMPLATE_FILE not found"
    exit 1
fi

# Generate alert rules by substituting variables
echo "Generating Prometheus alert rules..."
echo "  SYNC_ALERT_THRESHOLD: $SYNC_ALERT_THRESHOLD seconds"
echo "  Business Hours: $SYNC_START_HOUR:00 - $SYNC_END_HOUR:00"

# Use envsubst to substitute environment variables
# We need to escape the Prometheus template variables like {{ $value }}
envsubst '$SYNC_ALERT_THRESHOLD,$SYNC_START_HOUR,$SYNC_END_HOUR' < "$TEMPLATE_FILE" > "$OUTPUT_FILE"

echo "Alert rules generated successfully at $OUTPUT_FILE"