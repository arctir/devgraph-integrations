# Molecule Versioning

Each molecule maintains its own semantic version through metadata in its `__init__.py` file. Versions are automatically bumped based on conventional commits.

## Metadata Structure

Each molecule declares its version and capabilities:

```python
# devgraph_integrations/molecules/fossa/__init__.py
__version__ = "1.0.0"
__molecule_metadata__ = {
    "version": __version__,
    "name": "fossa",
    "display_name": "FOSSA",
    "description": "Discover FOSSA projects and create relations to repositories",
    "capabilities": ["discovery", "mcp", "relations"],
    "entity_types": ["FOSSAProject"],
    "relation_types": ["FOSSAProjectHostedByRepository"],
    "requires_auth": True,
    "auth_types": ["api_token"],
    "min_framework_version": "0.1.0",
}
```

## Version Bumping

Versions follow [Semantic Versioning](https://semver.org/) and are bumped based on conventional commit scopes:

### Commit Format

```
<type>(<scope>): <subject>

[body]

[BREAKING CHANGE: description]
```

### Bump Rules

- **BREAKING CHANGE** or `!` in subject → **MAJOR** version bump
- `feat(<molecule>):` → **MINOR** version bump
- `fix(<molecule>):` → **PATCH** version bump

### Examples

```bash
# Patch bump (1.0.0 → 1.0.1)
fix(fossa): handle missing repository URLs gracefully

# Minor bump (1.0.0 → 1.1.0)
feat(fossa): add support for custom FOSSA endpoints

# Major bump (1.0.0 → 2.0.0)
feat(fossa)!: change relation type to use standardized names

BREAKING CHANGE: FOSSAProjectRepository relation renamed to FOSSAProjectHostedByRepository
```

## Automatic Versioning

Use the provided script to bump versions based on commits:

```bash
# Bump all molecules based on commits since last tag
python scripts/bump-molecule-version.py

# Dry run (see what would change)
python scripts/bump-molecule-version.py --dry-run

# Bump specific molecule
python scripts/bump-molecule-version.py --molecule fossa

# Check commits since specific tag
python scripts/bump-molecule-version.py --since-tag v0.1.0
```

## Listing Molecules

View all molecules and their versions:

```bash
# Table format
devgraph-integrations list

# JSON format
devgraph-integrations list --json
```

Example output:
```
Molecule        Version    Capabilities                   Entity Types
====================================================================================================
FOSSA           1.0.0      discovery, mcp, relations      FOSSAProject
GitHub          1.2.0      discovery, mcp                 GitHubRepository, GitHubHostingService
GitLab          1.1.0      discovery, mcp                 GitLabProject, GitLabHostingService
```

## Capabilities

Molecules can declare these capabilities:

- `discovery` - Provides entity discovery
- `mcp` - Provides MCP server tools
- `relations` - Creates relations between entities
- `reconciliation` - Supports full state reconciliation
- `incremental` - Supports incremental updates
- `webhooks` - Supports webhook-based sync

## Deprecation

To deprecate a molecule:

```python
__molecule_metadata__ = {
    "version": "2.0.0",
    "deprecated": True,
    "replacement": "new-molecule-name",
    # ... other metadata
}
```

## Framework Compatibility

Molecules declare minimum framework version:

```python
__molecule_metadata__ = {
    "min_framework_version": "0.2.0",
    # ... other metadata
}
```

The framework validates compatibility at runtime and warns if versions mismatch.

## Best Practices

1. **Always use scoped commits** - Include molecule name in scope: `feat(fossa):`
2. **Document breaking changes** - Use `BREAKING CHANGE:` footer for major bumps
3. **Keep versions independent** - Each molecule versions independently
4. **Update metadata** - Keep capabilities and entity types accurate
5. **Test before bumping** - Run tests to ensure changes work
6. **Review auto-bumps** - Check generated versions make sense

## CI Integration

The GitHub Actions workflow validates conventional commits on PRs and can automatically bump versions on merge to main.
