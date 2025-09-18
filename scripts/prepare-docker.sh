#!/bin/bash
# Prepare Docker images for release

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Get version from source
VERSION=$(grep -E '^__version__' src/jira2solidtime/__version__.py | cut -d'"' -f2)
if [ -z "$VERSION" ]; then
    log_error "Could not extract version from __version__.py"
    exit 1
fi

log_info "Preparing Docker images for jira2solidtime v${VERSION}"

# Set default Docker username
if [ -z "$DOCKER_USERNAME" ]; then
    DOCKER_USERNAME="cddsab"
    log_info "Using default Docker Hub username: $DOCKER_USERNAME"
    log_info "Override with: export DOCKER_USERNAME=yourusername"
fi

# Clean previous builds
log_info "Cleaning previous Docker images"
docker rmi -f jira2solidtime:latest jira2solidtime:app 2>/dev/null || true

# Build full stack image
log_info "Building full stack Docker image"
docker build -f Dockerfile -t jira2solidtime:latest -t $DOCKER_USERNAME/jira2solidtime:latest -t $DOCKER_USERNAME/jira2solidtime:v$VERSION .

# Build app-only image
log_info "Building lightweight app-only Docker image"
docker build -f docker/Dockerfile.app -t jira2solidtime:app -t $DOCKER_USERNAME/jira2solidtime:latest-app -t $DOCKER_USERNAME/jira2solidtime:v$VERSION-app .

# Test images
log_info "Testing Docker images"
if docker run --rm jira2solidtime:latest uv run jira2solidtime --help >/dev/null; then
    log_success "Full stack image test passed"
else
    log_error "Full stack image test failed"
    exit 1
fi

if docker run --rm jira2solidtime:app --help >/dev/null; then
    log_success "App-only image test passed"
else
    log_error "App-only image test failed"
    exit 1
fi

# Show built images
log_info "Built Docker images:"
docker images | grep -E "(jira2solidtime|$DOCKER_USERNAME/jira2solidtime)"

log_success "Docker images ready for release!"
log_info "To push to Docker Hub:"
echo "  docker push $DOCKER_USERNAME/jira2solidtime:latest"
echo "  docker push $DOCKER_USERNAME/jira2solidtime:v$VERSION"
echo "  docker push $DOCKER_USERNAME/jira2solidtime:latest-app"
echo "  docker push $DOCKER_USERNAME/jira2solidtime:v$VERSION-app"
echo ""
log_info "To test locally:"
echo "  # Full stack with monitoring:"
echo "  docker-compose up -d"
echo ""
echo "  # App only:"
echo "  docker-compose -f compose/docker-compose.app.yml up -d"
echo ""
echo "  # Development:"
echo "  docker-compose -f compose/docker-compose.dev.yml up -d"