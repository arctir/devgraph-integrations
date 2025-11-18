# Release Scripts

## Release Process for OSS Repository

This repository uses semantic versioning: `vMAJOR.MINOR.PATCH`

**Examples:**
- `v0.1.0` - Initial release
- `v0.2.0` - Minor version with new features
- `v1.0.0` - Major version with breaking changes

### Creating a New Release

Run the release script from the repository root:

```bash
./scripts/release.sh
```

The script will:

1. **Show current version** from `pyproject.toml`
2. **Check git tag consistency** and warn if out of sync
3. **Prompt for new version** with validation
4. **Update `pyproject.toml`** with the new version
5. **Create a commit** with the version bump
6. **Create an annotated tag** with release notes
7. **Push to GitHub** which triggers the release workflow

### What Happens Next

After pushing the tag, GitHub Actions will automatically:

1. Build multi-platform Docker images (amd64, arm64)
2. Push images to GitHub Container Registry with tags:
   - `ghcr.io/arctir/devgraph-integrations:v0.1.0`
   - `ghcr.io/arctir/devgraph-integrations:v0.1`
   - `ghcr.io/arctir/devgraph-integrations:v0`
   - `ghcr.io/arctir/devgraph-integrations:latest`
3. Run tests on the image
4. Create a GitHub Release with auto-generated release notes
5. Generate and upload a release manifest

### Version Consistency

The script checks that `pyproject.toml` version matches the latest git tag. If they're out of sync, you'll see:

```
WARNING: Version mismatch detected!
  pyproject.toml: 0.1.0
  Latest git tag: v0.0.9
```

This helps ensure the repository stays consistent.

### After OSS Release

After creating an OSS release, you'll want to create a corresponding internal release:

```bash
cd ../devgraph-integrations-internal
./scripts/release.sh
```

This will create an internal release like `v0.1.0-arctir.1` that tracks the OSS version.

### Semantic Versioning Guidelines

- **PATCH** (`v0.1.0` → `v0.1.1`): Bug fixes, minor changes
- **MINOR** (`v0.1.0` → `v0.2.0`): New features, backward compatible
- **MAJOR** (`v0.1.0` → `v1.0.0`): Breaking changes

### Example Session

```
INFO: Current version in pyproject.toml: 0.1.0
INFO: Last git tag: v0.1.0
SUCCESS: pyproject.toml and git tag are in sync

Enter new version (current: 0.1.0):
  Format: MAJOR.MINOR.PATCH (e.g., 0.1.0, 0.2.0, 1.0.0)
New version: 0.2.0

Release Summary:
  Current Version: 0.1.0
  New Version:     0.2.0
  Git Tag:         v0.2.0

Create release v0.2.0? (y/N): y
INFO: Updating pyproject.toml version to 0.2.0...
INFO: Creating version bump commit...
INFO: Creating tag v0.2.0...
INFO: Pushing changes and tag to remote...
SUCCESS: Release v0.2.0 created successfully!
```

### Manual Release (Alternative)

If you prefer to create releases manually:

```bash
# 1. Update pyproject.toml
NEW_VERSION="0.2.0"
sed -i "s/^version = .*/version = \"$NEW_VERSION\"/" pyproject.toml

# 2. Commit and tag
git add pyproject.toml
git commit -s -m "chore: bump version to $NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"

# 3. Push
git push origin main
git push origin "v$NEW_VERSION"
```

### Checking Versions

```bash
# Current version in pyproject.toml
grep '^version = ' pyproject.toml

# Latest git tag
git describe --tags --abbrev=0

# All tags
git tag -l
```

### Troubleshooting

**Error: "Version must be in format X.Y.Z"**
- Use semantic versioning format: `0.1.0`, `1.0.0`, etc.

**Error: "Tag already exists"**
- Choose a different version number
- Or delete the existing tag: `git tag -d v0.1.0`

**Warning: "Version mismatch detected"**
- This means `pyproject.toml` and git tags are out of sync
- Decide which version is correct and proceed
- Consider manually fixing the inconsistency first
