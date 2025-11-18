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
3. **Analyze commits** since last tag using conventional commits
4. **Suggest version bump** based on commit types:
   - `feat!:` or `BREAKING CHANGE:` → MAJOR bump (0.1.0 → 1.0.0)
   - `feat:` → MINOR bump (0.1.0 → 0.2.0)
   - `fix:` → PATCH bump (0.1.0 → 0.1.1)
5. **Prompt for new version** with suggested default (can override)
6. **Update `pyproject.toml`** with the new version
7. **Generate CHANGELOG.md** from conventional commits
8. **Create a commit** with the version bump
9. **Create an annotated tag** with release notes and changelog
10. **Push to GitHub** which triggers the release workflow

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

INFO: Analyzing commits since v0.1.0 for version suggestion...

Commits since v0.1.0:
  Features: 3
    feat(github): add webhook support
    feat(gitlab): add project discovery
    feat: add Docker provider
  Fixes: 2
    fix(core): handle rate limiting
    fix(config): validate selectors

SUCCESS: Suggested version: 0.2.0 (MINOR (new features detected))

Enter new version (current: 0.1.0, suggested: 0.2.0):
  Format: MAJOR.MINOR.PATCH (e.g., 0.1.0, 0.2.0, 1.0.0)
New version [0.2.0]: ⏎  (press Enter to accept suggestion)

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

## Conventional Commits Integration

The release script analyzes commits since the last tag to suggest the appropriate version bump.

### Commit Type Detection

The script looks for these conventional commit patterns:

| Commit Type | Pattern | Version Bump | Example |
|-------------|---------|--------------|---------|
| Breaking Change | `feat!:`, `fix!:`, `BREAKING CHANGE:` | MAJOR (1.0.0) | `feat!: redesign API` |
| Feature | `feat:`, `feat(scope):` | MINOR (0.1.0) | `feat(github): add webhooks` |
| Bug Fix | `fix:`, `fix(scope):` | PATCH (0.0.1) | `fix(core): handle errors` |
| Other | `chore:`, `docs:`, `test:`, etc. | PATCH (0.0.1) | `chore: update deps` |

### Version Bump Logic

1. **If any breaking changes found** → MAJOR bump
   - `feat!: redesign config system`
   - `fix!: remove deprecated API`
   - Commits with `BREAKING CHANGE:` in body

2. **Else if any features found** → MINOR bump
   - `feat(gitlab): add project discovery`
   - `feat: support Docker registry`

3. **Else if any fixes found** → PATCH bump
   - `fix(github): handle rate limits`
   - `fix: correct selector validation`

4. **Else** → PATCH bump (for other changes)
   - `chore: update dependencies`
   - `docs: improve README`

### Example: Breaking Change Detection

```bash
# These commits would suggest MAJOR bump:
git commit -m "feat!: change configuration format

BREAKING CHANGE: Config files must now use YAML instead of JSON"

git commit -m "refactor!: remove legacy API endpoints"
```

### Example: Feature Detection

```bash
# These commits would suggest MINOR bump:
git commit -m "feat(github): add webhook support"
git commit -m "feat(docker): support multi-platform builds"
git commit -m "fix(core): handle errors gracefully"
```

### Example: Patch Detection

```bash
# These commits would suggest PATCH bump:
git commit -m "fix(config): validate required fields"
git commit -m "fix(github): correct rate limit handling"
```

### Overriding Suggestions

The script suggests a version but you can always override it:

```
SUCCESS: Suggested version: 0.2.0 (MINOR (new features detected))

Enter new version (current: 0.1.0, suggested: 0.2.0):
  Format: MAJOR.MINOR.PATCH (e.g., 0.1.0, 0.2.0, 1.0.0)
New version [0.2.0]: 1.0.0  ← You can override to MAJOR if you prefer
```

### Best Practices

1. **Use conventional commits** throughout development
2. **Review the commit summary** before accepting the suggestion
3. **Override if needed** - the script is a helper, not a requirement
4. **Document breaking changes** clearly in commit messages

## Automatic Changelog Generation

The release script automatically generates and maintains a `CHANGELOG.md` file based on conventional commits.

### Changelog Structure

Each release creates a new entry with the following sections (when applicable):

- **⚠ BREAKING CHANGES** - For commits with `feat!:`, `fix!:`, or `BREAKING CHANGE:` in the body
- **✨ Features** - For commits starting with `feat:` or `feat(scope):`
- **🐛 Bug Fixes** - For commits starting with `fix:` or `fix(scope):`
- **🔧 Other Changes** - For all other commits (chore, docs, test, etc.)

### Example Changelog Entry

```markdown
## [0.2.0] - 2025-11-18

### ✨ Features

- feat(github): add webhook support for real-time updates
- feat(gitlab): add project discovery
- feat(docker): support multi-platform image builds

### 🐛 Bug Fixes

- fix(core): handle rate limiting gracefully
- fix(config): validate required selector fields

### 🔧 Other Changes

- chore: update dependencies to latest versions
- docs: improve README with examples
```

### Changelog Workflow

1. **First Release**: If no `CHANGELOG.md` exists, the script creates one with:
   ```markdown
   # Changelog

   ## [0.1.0] - 2025-11-18
   ...
   ```

2. **Subsequent Releases**: New entries are inserted after the title, keeping the most recent release at the top:
   ```markdown
   # Changelog

   ## [0.2.0] - 2025-11-18
   <new changes>

   ## [0.1.0] - 2025-11-17
   <old changes>
   ```

3. **Git Tag Annotation**: The changelog entry is included in the annotated git tag message, making it visible in GitHub releases

### Changelog Best Practices

1. **Write descriptive commit messages** - These become your changelog entries
2. **Use scopes** for clarity - `feat(github):` is more informative than `feat:`
3. **Group related changes** - Multiple commits on the same feature will all appear
4. **Document breaking changes** thoroughly - These get special prominence

### Example: Full Changelog Workflow

```bash
# Make changes and commit using conventional commits
git commit -m "feat(gitlab): add project discovery"
git commit -m "feat(docker): support private registries"
git commit -m "fix(github): handle rate limit errors"
git commit -m "docs: update installation guide"

# Run release script
./scripts/release.sh

# The script will:
# 1. Analyze these 4 commits
# 2. Suggest MINOR bump (new features detected)
# 3. Generate changelog entry:
#    ### ✨ Features
#    - feat(gitlab): add project discovery
#    - feat(docker): support private registries
#
#    ### 🐛 Bug Fixes
#    - fix(github): handle rate limit errors
#
#    ### 🔧 Other Changes
#    - docs: update installation guide
# 4. Update/create CHANGELOG.md
# 5. Commit the changes
# 6. Create annotated tag with changelog
```

### Manual Changelog Editing

While the script generates the changelog automatically, you can:

1. **Edit before committing** - After the script updates `CHANGELOG.md`, you can manually edit it before the commit is created
2. **Add additional context** - Expand on generated entries with more details
3. **Reorganize entries** - Group or reorder items for better readability

The changelog is just markdown, so feel free to enhance it as needed.

### Viewing Changelogs

**In the repository:**
```bash
cat CHANGELOG.md
```

**In git tags:**
```bash
git tag -l -n20 v0.2.0
```

**On GitHub:**
- Releases page shows the annotated tag message (includes changelog)
- `CHANGELOG.md` file is visible in the repository root
