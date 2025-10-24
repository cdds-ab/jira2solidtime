#!/bin/bash
set -e

echo "🔨 Rebuilding jira2solidtime..."

# Stop and remove old containers
echo "⏹️  Stopping containers..."
docker compose down

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
