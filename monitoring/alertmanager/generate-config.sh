#!/bin/bash
set -e

echo "Generating Alertmanager configuration from template..."

# Use envsubst to substitute environment variables
envsubst < /alertmanager.template.yml > /etc/alertmanager/alertmanager.yml

echo "Generated configuration:"
cat /etc/alertmanager/alertmanager.yml

echo "Starting Alertmanager..."
exec /bin/alertmanager "$@"