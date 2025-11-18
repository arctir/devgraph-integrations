#!/bin/bash
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    exit 1
}

info() {
    echo -e "${BLUE}INFO: $1${NC}"
}

success() {
    echo -e "${GREEN}SUCCESS: $1${NC}"
}

warn() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] || ! grep -q "devgraph-integrations" pyproject.toml || grep -q "devgraph-integrations-internal" pyproject.toml; then
    error "Must be run from devgraph-integrations repository root"
fi

# Get current version from pyproject.toml
CURRENT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
info "Current version in pyproject.toml: $CURRENT_VERSION"

# Get last git tag
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo "")
if [ -n "$LAST_TAG" ]; then
    info "Last git tag: v$LAST_TAG"

    # Check if they match
    if [ "$CURRENT_VERSION" != "$LAST_TAG" ]; then
        warn "Version mismatch detected!"
        warn "  pyproject.toml: $CURRENT_VERSION"
        warn "  Latest git tag: v$LAST_TAG"
    else
        success "pyproject.toml and git tag are in sync"
    fi
fi

# Prompt for new version
echo ""
echo "Enter new version (current: $CURRENT_VERSION):"
echo "  Format: MAJOR.MINOR.PATCH (e.g., 0.1.0, 0.2.0, 1.0.0)"
read -p "New version: " NEW_VERSION

# Validate version format
if ! [[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    error "Version must be in format X.Y.Z (e.g., 0.1.0)"
fi

# Check if version is newer
if [ "$NEW_VERSION" = "$CURRENT_VERSION" ]; then
    error "New version must be different from current version"
fi

FULL_VERSION="v${NEW_VERSION}"

# Check if tag already exists
if git rev-parse "$FULL_VERSION" >/dev/null 2>&1; then
    error "Tag $FULL_VERSION already exists"
fi

# Confirm release
echo ""
echo "Release Summary:"
echo "  Current Version: $CURRENT_VERSION"
echo "  New Version:     $NEW_VERSION"
echo "  Git Tag:         $FULL_VERSION"
echo ""
read -p "Create release $FULL_VERSION? (y/N): " CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    warn "Release cancelled"
    exit 0
fi

# Update pyproject.toml version
info "Updating pyproject.toml version to $NEW_VERSION..."
sed -i "s/^version = .*/version = \"$NEW_VERSION\"/" pyproject.toml

# Stage the change
git add pyproject.toml

# Commit version bump
info "Creating version bump commit..."
git commit -s -m "chore: bump version to $NEW_VERSION" || {
    warn "No changes to commit (version may already be set)"
}

# Create annotated tag
info "Creating tag $FULL_VERSION..."
git tag -a "$FULL_VERSION" -m "Release $FULL_VERSION

Open-source release of devgraph-integrations"

# Push changes
info "Pushing changes and tag to remote..."
git push origin main
git push origin "$FULL_VERSION"

success "Release $FULL_VERSION created successfully!"
echo ""
info "GitHub will automatically build and publish:"
info "  - Docker images to ghcr.io/arctir/devgraph-integrations"
info "  - GitHub Release with auto-generated notes"
info ""
info "View the release at: https://github.com/arctir/devgraph-integrations/releases/tag/$FULL_VERSION"
echo ""
warn "REMINDER: After this OSS release is complete, you may want to create"
warn "a corresponding internal release with: cd ../devgraph-integrations-internal && ./scripts/release.sh"
