# Creating Custom Molecules

A molecule is a plugin that integrates external services with devgraph. Each molecule can provide multiple capabilities: entity discovery, MCP server tools, and relationship mapping.

## Quick Start

### 1. Create the molecule structure

```
my_package/
  molecules/
    example/
      __init__.py
      molecule.py      # Required: molecule facade
      provider.py      # Optional: discovery provider
      mcp.py           # Optional: MCP server
```

### 2. Create the molecule facade

```python
# my_package/molecules/example/molecule.py

from typing import Any, Dict, Optional, Type
from devgraph_integrations.core.molecule import Molecule

class ExampleMolecule(Molecule):
    """Example molecule providing discovery capability."""

    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        return {
            "name": "example",
            "display_name": "Example Service",
            "description": "Discover entities from Example Service",
            "version": "1.0.0",
            "capabilities": ["discovery"],  # or ["discovery", "mcp"]
            "logo": {"reactIcons": "SiExample"},
            "entity_types": ["ExampleEntity"],
            "relation_types": [],
            "requires_auth": True,
            "auth_types": ["api_key"],
        }

    @staticmethod
    def get_discovery_provider() -> Optional[Type[Any]]:
        from .provider import ExampleProvider
        return ExampleProvider

    @staticmethod
    def get_mcp_server() -> Optional[Type[Any]]:
        # Return None if no MCP capability
        return None
```

### 3. Register in pyproject.toml

```toml
[tool.poetry.plugins."devgraph.molecules"]
"example.molecules.devgraph.ai" = "my_package.molecules.example.molecule:ExampleMolecule"
```

### 4. Install and verify

```bash
poetry install
devgraph-integrations list
```

## Metadata Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Machine-readable identifier (e.g., "github") |
| `display_name` | Yes | Human-readable name (e.g., "GitHub") |
| `description` | Yes | Brief description of functionality |
| `version` | Yes | Semantic version (e.g., "1.0.0") |
| `capabilities` | Yes | List: `["discovery"]`, `["mcp"]`, or `["discovery", "mcp"]` |
| `logo` | No | `{"reactIcons": "SiGithub"}` or `{"url": "..."}` |
| `entity_types` | No | Entity types this molecule creates |
| `relation_types` | No | Relation types this molecule creates |
| `requires_auth` | No | Whether authentication is required |
| `auth_types` | No | Supported auth: `["pat", "api_key", "oauth"]` |
| `homepage_url` | No | Service homepage URL |
| `docs_url` | No | Documentation URL |

## Discovery Provider

If your molecule has the `discovery` capability, implement a provider:

```python
# my_package/molecules/example/provider.py

from devgraph_integrations.core.provider import EntityProvider, ProviderConfig

class ExampleProvider(EntityProvider):
    """Discover entities from Example Service."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_key = config.config.get("api_key")

    async def discover(self):
        """Discover and yield entities."""
        # Fetch data from your service
        items = await self._fetch_items()

        for item in items:
            yield {
                "type": "ExampleEntity",
                "id": item["id"],
                "name": item["name"],
                "properties": {
                    "url": item["url"],
                    # ... other properties
                }
            }

    async def _fetch_items(self):
        # Your API calls here
        pass
```

## MCP Server

If your molecule has the `mcp` capability, implement an MCP server:

```python
# my_package/molecules/example/mcp.py

from devgraph.mcpserver.pluginmanager import DevgraphMCPPluginManager

class ExampleMCPServer:
    """MCP server for Example Service."""

    def __init__(self, config):
        self.config = config

    @DevgraphMCPPluginManager.mcp_tool
    async def get_example_data(self, item_id: str) -> dict:
        """Get data for a specific item.

        Args:
            item_id: The item identifier

        Returns:
            Item data dictionary
        """
        # Implement your tool logic
        return {"id": item_id, "data": "..."}
```

## Configuration

Molecules receive configuration from the YAML config file:

```yaml
discovery:
  molecules:
    - name: my-example
      type: example
      every: 300
      config:
        api_key: "your-api-key"
        # ... other config options
```

The `config` section is passed to your provider's `ProviderConfig.config`.

## Testing

```python
# tests/test_molecule.py

from my_package.molecules.example.molecule import ExampleMolecule

def test_metadata():
    meta = ExampleMolecule.get_metadata()
    assert meta["name"] == "example"
    assert "discovery" in meta["capabilities"]

def test_has_discovery():
    provider = ExampleMolecule.get_discovery_provider()
    assert provider is not None

def test_capabilities():
    assert ExampleMolecule.has_capability("discovery")
    assert not ExampleMolecule.has_capability("mcp")
```

## Best Practices

1. **Lazy imports**: Import providers/MCP servers inside the getter methods to avoid loading dependencies when not needed
2. **Error handling**: Wrap imports in try/except if dependencies are optional
3. **Semantic versioning**: Use semver for the version field
4. **Descriptive metadata**: Provide clear descriptions and entity types
5. **Authentication**: Document required auth in `auth_types`

## Examples

See existing molecules for reference:
- [GitHub](../devgraph_integrations/molecules/github/) - Discovery + MCP
- [GitLab](../devgraph_integrations/molecules/gitlab/) - Discovery + MCP
- [Docker](../devgraph_integrations/molecules/docker/) - Discovery only
- [LDAP](../devgraph_integrations/molecules/ldap/) - Discovery only
