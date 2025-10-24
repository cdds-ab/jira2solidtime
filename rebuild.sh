#!/bin/bash
set -e

echo "🔨 Rebuilding jira2solidtime..."

# Stop and remove old containers
echo "⏹️  Stopping containers..."
docker compose down

# Ensure data directory has correct permissions for non-root user
echo "🔧 Setting data directory permissions..."
mkdir -p data
sudo chown -R 1000:1000 data || chown -R 1000:1000 data 2>/dev/null || echo "⚠️  Could not set permissions, may need sudo"

# Rebuild images
echo "🏗️  Building fresh image..."
docker compose build --no-cache

# Start containers
echo "🚀 Starting containers..."
docker compose up -d

echo ""
echo "✅ Done! Service running on http://localhost:8080"
echo ""
echo "📊 View logs:"
echo "   docker compose logs -f"
echo ""
echo "🛑 Stop:"
echo "   docker compose down"
