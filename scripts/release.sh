#!/bin/bash
# Release script for jira2solidtime using semantic versioning

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
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
    exit 1
}

# Check if we're on master branch
current_branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$current_branch" != "master" ]; then
    log_error "Must be on master branch to release. Current branch: $current_branch"
fi

# Check if working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    log_error "Working directory is not clean. Please commit or stash changes."
fi

# Get current version
current_version=$(python -c "from src.jira2solidtime.__version__ import __version__; print(__version__)")
log_info "Current version: $current_version"

# Parse version numbers
IFS='.' read -ra VERSION_PARTS <<< "$current_version"
major=${VERSION_PARTS[0]}
minor=${VERSION_PARTS[1]}
patch=${VERSION_PARTS[2]}

# Release type
echo "What type of release?"
echo "1) patch (${major}.${minor}.$((patch + 1)))"
echo "2) minor (${major}.$((minor + 1)).0)"
echo "3) major ($((major + 1)).0.0)"
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        new_version="${major}.${minor}.$((patch + 1))"
        release_type="patch"
        ;;
    2)
        new_version="${major}.$((minor + 1)).0"
        release_type="minor"
        ;;
    3)
        new_version="$((major + 1)).0.0"
        release_type="major"
        ;;
    *)
        log_error "Invalid choice"
        ;;
esac

log_info "Releasing version $new_version ($release_type)"

# Confirm release
read -p "Continue with release $new_version? [y/N]: " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    log_warning "Release cancelled"
    exit 0
fi

# Update version file
log_info "Updating version to $new_version"
sed -i "s/__version__ = \".*\"/__version__ = \"$new_version\"/" src/jira2solidtime/__version__.py

# Run quality checks
log_info "Running quality checks..."
uv run ruff check --fix .
uv run ruff format .
uv run mypy .
uv run pytest

# Commit version bump
log_info "Committing version bump"
git add src/jira2solidtime/__version__.py
git commit -m "chore: bump version to $new_version"

# Create and push tag
log_info "Creating and pushing tag v$new_version"
git tag -a "v$new_version" -m "Release version $new_version"
git push origin master
git push origin "v$new_version"

# Generate changelog entry
log_info "Generating changelog entry"
echo "" >> CHANGELOG.md.tmp
echo "## [v$new_version] - $(date +%Y-%m-%d)" >> CHANGELOG.md.tmp
echo "" >> CHANGELOG.md.tmp
echo "### Changes" >> CHANGELOG.md.tmp
echo "- Release $new_version" >> CHANGELOG.md.tmp

if [ -f CHANGELOG.md ]; then
    cat CHANGELOG.md >> CHANGELOG.md.tmp
    mv CHANGELOG.md.tmp CHANGELOG.md
else
    echo "# Changelog" > CHANGELOG.md
    echo "" >> CHANGELOG.md
    echo "All notable changes to this project will be documented in this file." >> CHANGELOG.md
    cat CHANGELOG.md.tmp >> CHANGELOG.md
    rm CHANGELOG.md.tmp
fi

git add CHANGELOG.md
git commit -m "docs: update changelog for v$new_version"
git push origin master

log_success "Successfully released version $new_version!"
log_info "Tag: v$new_version"
log_info "You can now create a GitHub release from: https://github.com/your-repo/releases/new?tag=v$new_version"