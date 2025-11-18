# Extension Points

This document describes the extension points available in devgraph-integrations for internal deployments.

## Configuration Sources

The configuration system uses stevedore to allow pluggable configuration sources. The default implementation loads configuration from YAML files, but internal deployments can add additional sources like APIs or databases.

### Creating a Custom Config Source

1. Implement the `ConfigSource` interface:

```python
from devgraph_integrations.config.sources import ConfigSource, ConfigSourceError
from typing import Any

class APIConfigSource(ConfigSource):
    """Load configuration from an internal API."""

    def supports(self, source_id: str) -> bool:
        """Check if source_id is an API URL."""
        return source_id.startswith("https://api.internal/")

    def load(self, source_id: str, **kwargs) -> dict[str, Any]:
        """Load configuration from API.

        Args:
            source_id: API endpoint URL
            **kwargs: Additional parameters (e.g., environment_id, auth_token)

        Returns:
            Configuration dictionary

        Raises:
            ConfigSourceError: If API request fails
        """
        import requests

        response = requests.get(
            source_id,
            params={"environment_id": kwargs.get("environment_id")},
            headers={"Authorization": f"Bearer {kwargs.get('auth_token')}"}
        )

        if not response.ok:
            raise ConfigSourceError(f"API request failed: {response.status_code}")

        return response.json()
```

2. Register the plugin in your internal package's `pyproject.toml`:

```toml
[tool.poetry.plugins."devgraph_integrations.config.sources"]
"api" = "devgraph_internal.config:APIConfigSource"
```

3. Use the custom source:

```python
from devgraph_integrations.config import Config

# Explicitly specify source type
config = Config.from_source(
    "https://api.internal/config",
    source_type="api",
    environment_id="prod",
    auth_token="xxx"
)

# Or let it auto-detect based on URL pattern
config = Config.from_source("https://api.internal/config")
```

## Database Integration

For features that require database access (like provider version checking), create internal-only modules that import from the internal `devgraph` package. These modules should not be included in the public distribution.

Example structure:

```
devgraph-internal/
├── pyproject.toml
├── devgraph_internal/
│   ├── config.py           # APIConfigSource implementation
│   ├── version_checker.py  # Database-backed version checking
│   └── ...
```

## Provider Extensions

The provider system already uses stevedore for discovery. To add internal-only providers:

1. Create your provider class extending the base `Provider`
2. Register it via stevedore in your internal package
3. Reference it in configuration by the plugin name

## Discovery Extensions

The `DiscoveryExtensionManager` class provides hooks for extending discovery behavior. Internal deployments can use this to add custom processing logic for entities and relations.

See `devgraph_integrations/core/extension.py` for available hooks.
