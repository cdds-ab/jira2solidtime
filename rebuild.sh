#!/bin/bash
set -e

echo "🔨 Rebuilding jira2solidtime..."

# Export host UID/GID for docker-compose.override.yml
export UID=$(id -u)
export GID=$(id -g)

# Stop and remove old containers
echo "⏹️  Stopping containers..."
docker compose down

# Create data directory (permissions handled by UID mapping)
echo "🔧 Creating data directory..."
mkdir -p data

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
