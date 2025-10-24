#!/bin/bash
set -e

# Ensure data directory exists and has correct permissions
# This is needed because Docker volume mounts can override ownership
if [ ! -w /app/data ]; then
    echo "⚠️  Warning: /app/data is not writable"
    echo "   If running as non-root, ensure the host directory has correct permissions:"
    echo "   sudo chown -R 1000:1000 ./data"
fi

# Create data directory if it doesn't exist
mkdir -p /app/data

# Execute the main command
exec "$@"
