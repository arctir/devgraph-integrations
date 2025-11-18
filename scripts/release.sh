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

# Analyze commits since last tag for version suggestion
if [ -n "$LAST_TAG" ]; then
    echo ""
    info "Analyzing commits since v$LAST_TAG for version suggestion..."

    # Get commits since last tag
    COMMITS=$(git log "v${LAST_TAG}..HEAD" --pretty=format:"%s" 2>/dev/null || echo "")

    if [ -n "$COMMITS" ]; then
        # Count different commit types
        BREAKING_COUNT=$(echo "$COMMITS" | grep -cE '^(feat|fix|perf|refactor)!:|BREAKING CHANGE:' || echo 0)
        FEAT_COUNT=$(echo "$COMMITS" | grep -cE '^feat(\(.*\))?:' || echo 0)
        FIX_COUNT=$(echo "$COMMITS" | grep -cE '^fix(\(.*\))?:' || echo 0)

        # Determine suggested bump
        IFS='.' read -r MAJOR MINOR PATCH <<< "$LAST_TAG"

        if [ "$BREAKING_COUNT" -gt 0 ]; then
            SUGGESTED_MAJOR=$((MAJOR + 1))
            SUGGESTED_MINOR=0
            SUGGESTED_PATCH=0
            BUMP_TYPE="MAJOR (breaking changes detected)"
        elif [ "$FEAT_COUNT" -gt 0 ]; then
            SUGGESTED_MAJOR=$MAJOR
            SUGGESTED_MINOR=$((MINOR + 1))
            SUGGESTED_PATCH=0
            BUMP_TYPE="MINOR (new features detected)"
        elif [ "$FIX_COUNT" -gt 0 ]; then
            SUGGESTED_MAJOR=$MAJOR
            SUGGESTED_MINOR=$MINOR
            SUGGESTED_PATCH=$((PATCH + 1))
            BUMP_TYPE="PATCH (bug fixes detected)"
        else
            SUGGESTED_MAJOR=$MAJOR
            SUGGESTED_MINOR=$MINOR
            SUGGESTED_PATCH=$((PATCH + 1))
            BUMP_TYPE="PATCH (other changes)"
        fi

        SUGGESTED_VERSION="${SUGGESTED_MAJOR}.${SUGGESTED_MINOR}.${SUGGESTED_PATCH}"

        # Show commit summary
        echo ""
        echo -e "${BLUE}Commits since v${LAST_TAG}:${NC}"
        if [ "$BREAKING_COUNT" -gt 0 ]; then
            echo -e "  ${RED}Breaking changes: $BREAKING_COUNT${NC}"
            echo "$COMMITS" | grep -E '^(feat|fix|perf|refactor)!:|BREAKING CHANGE:' | sed 's/^/    /' || true
        fi
        if [ "$FEAT_COUNT" -gt 0 ]; then
            echo -e "  ${GREEN}Features: $FEAT_COUNT${NC}"
            echo "$COMMITS" | grep -E '^feat(\(.*\))?:' | sed 's/^/    /' || true
        fi
        if [ "$FIX_COUNT" -gt 0 ]; then
            echo -e "  ${YELLOW}Fixes: $FIX_COUNT${NC}"
            echo "$COMMITS" | grep -E '^fix(\(.*\))?:' | sed 's/^/    /' || true
        fi

        echo ""
        success "Suggested version: $SUGGESTED_VERSION ($BUMP_TYPE)"
    else
        warn "No commits found since last tag"
        SUGGESTED_VERSION=""
    fi
else
    warn "No previous tags found, cannot analyze commits"
    SUGGESTED_VERSION=""
fi

# Prompt for new version
echo ""
if [ -n "$SUGGESTED_VERSION" ]; then
    echo "Enter new version (current: $CURRENT_VERSION, suggested: $SUGGESTED_VERSION):"
    echo "  Format: MAJOR.MINOR.PATCH (e.g., 0.1.0, 0.2.0, 1.0.0)"
    read -p "New version [$SUGGESTED_VERSION]: " NEW_VERSION
    NEW_VERSION=${NEW_VERSION:-$SUGGESTED_VERSION}
else
    echo "Enter new version (current: $CURRENT_VERSION):"
    echo "  Format: MAJOR.MINOR.PATCH (e.g., 0.1.0, 0.2.0, 1.0.0)"
    read -p "New version: " NEW_VERSION
fi

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

# Generate changelog entry
CHANGELOG_ENTRY=""
if [ -n "$LAST_TAG" ] && [ -n "$COMMITS" ]; then
    info "Generating changelog entry..."

    CHANGELOG_ENTRY="## [$NEW_VERSION] - $(date +%Y-%m-%d)

"

    # Add breaking changes section if any
    if [ "$BREAKING_COUNT" -gt 0 ]; then
        CHANGELOG_ENTRY+="### ⚠ BREAKING CHANGES

"
        BREAKING_COMMITS=$(echo "$COMMITS" | grep -E '^(feat|fix|perf|refactor)!:|BREAKING CHANGE:' || echo "")
        while IFS= read -r commit; do
            CHANGELOG_ENTRY+="- $commit
"
        done <<< "$BREAKING_COMMITS"
        CHANGELOG_ENTRY+="
"
    fi

    # Add features section if any
    if [ "$FEAT_COUNT" -gt 0 ]; then
        CHANGELOG_ENTRY+="### ✨ Features

"
        FEAT_COMMITS=$(echo "$COMMITS" | grep -E '^feat(\(.*\))?:' || echo "")
        while IFS= read -r commit; do
            CHANGELOG_ENTRY+="- $commit
"
        done <<< "$FEAT_COMMITS"
        CHANGELOG_ENTRY+="
"
    fi

    # Add fixes section if any
    if [ "$FIX_COUNT" -gt 0 ]; then
        CHANGELOG_ENTRY+="### 🐛 Bug Fixes

"
        FIX_COMMITS=$(echo "$COMMITS" | grep -E '^fix(\(.*\))?:' || echo "")
        while IFS= read -r commit; do
            CHANGELOG_ENTRY+="- $commit
"
        done <<< "$FIX_COMMITS"
        CHANGELOG_ENTRY+="
"
    fi

    # Add other commits
    OTHER_COMMITS=$(echo "$COMMITS" | grep -vE '^(feat|fix)(\(.*\))?:|^(feat|fix|perf|refactor)!:|BREAKING CHANGE:' || echo "")
    if [ -n "$OTHER_COMMITS" ]; then
        CHANGELOG_ENTRY+="### 🔧 Other Changes

"
        while IFS= read -r commit; do
            [ -n "$commit" ] && CHANGELOG_ENTRY+="- $commit
"
        done <<< "$OTHER_COMMITS"
    fi
fi

# Update or create CHANGELOG.md
if [ -f "CHANGELOG.md" ]; then
    info "Updating CHANGELOG.md..."
    # Insert new entry after the title
    if [ -n "$CHANGELOG_ENTRY" ]; then
        # Create temporary file with new entry
        {
            head -n 2 CHANGELOG.md  # Keep title and blank line
            echo "$CHANGELOG_ENTRY"
            tail -n +3 CHANGELOG.md  # Append rest of file
        } > CHANGELOG.md.tmp
        mv CHANGELOG.md.tmp CHANGELOG.md
        git add CHANGELOG.md
    fi
else
    info "Creating CHANGELOG.md..."
    if [ -n "$CHANGELOG_ENTRY" ]; then
        cat > CHANGELOG.md << EOF
# Changelog

$CHANGELOG_ENTRY
EOF
        git add CHANGELOG.md
    fi
fi

# Create annotated tag with changelog
info "Creating tag $FULL_VERSION..."
TAG_MESSAGE="Release $FULL_VERSION

"
if [ -n "$CHANGELOG_ENTRY" ]; then
    TAG_MESSAGE+="$CHANGELOG_ENTRY"
else
    TAG_MESSAGE+="Open-source release of devgraph-integrations"
fi

git tag -a "$FULL_VERSION" -m "$TAG_MESSAGE"

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
