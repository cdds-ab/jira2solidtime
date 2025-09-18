#!/bin/bash
# Generate Alertmanager configuration from template with environment variables

set -e

# Check if required environment variables are set
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "Error: TELEGRAM_BOT_TOKEN environment variable is required"
    exit 1
fi

if [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo "Error: TELEGRAM_CHAT_ID environment variable is required"
    exit 1
fi

echo "Generating Alertmanager configuration..."
envsubst < monitoring/alertmanager/alertmanager.template.yml > monitoring/alertmanager/alertmanager.yml

echo "✅ Alertmanager configuration generated successfully"
echo "   Bot token: ${TELEGRAM_BOT_TOKEN:0:10}..."
echo "   Chat ID: $TELEGRAM_CHAT_ID"