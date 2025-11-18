# Devgraph Molecules

Molecules are units of functionality for systems of record that extend Devgraph's capability to discover and integrate with various external systems. Each molecule can provide:
- **Discovery providers** - Discover entities and relationships from external systems
- **MCP tools** - Model Context Protocol tools for AI assistant integration
- **Both** - Combined discovery and MCP capabilities

Molecules implement a consistent pattern to create entities and relationships in the Devgraph ontology.

## Overview

The molecules framework provides a pluggable architecture for integrating with different platforms, services, and data sources. Each molecule follows consistent patterns for configuration, entity creation, and relationship management while adapting to the specific requirements of its target system.

## Available Molecules

### [GitHub](./github/)
Integrates with GitHub's API to discover repositories and hosting services.
- **Entities**: GitHub repositories, hosting services
- **Use Cases**: Source code discovery, repository metadata management
- **Authentication**: GitHub personal access token

### [Argo CD](./argo/)
Connects to Argo CD instances to discover GitOps applications and projects.
- **Entities**: Argo instances, projects, applications
- **Use Cases**: Deployment tracking, GitOps relationship mapping
- **Authentication**: Argo CD API token

### [Vercel](./vercel/)
Integrates with Vercel's deployment platform to discover projects and deployments.
- **Entities**: Teams, projects, deployments
- **Use Cases**: Frontend deployment tracking, team organization
- **Authentication**: Vercel API token

### [LDAP](./ldap/)
Connects to LDAP directories to discover users, groups, and organizational units.
- **Entities**: Users, groups, organizational units
- **Use Cases**: Identity management, organizational structure mapping
- **Authentication**: LDAP bind credentials or anonymous access

### [Devgraph MCP](./devgraph/)
Provides Model Context Protocol (MCP) integration for external tool access.
- **Purpose**: Enable AI assistants and external tools to query Devgraph
- **Use Cases**: AI-powered knowledge exploration, external integrations
- **Authentication**: Optional Devgraph API key

## Architecture

### Provider Pattern
All molecules implement the `Provider` abstract base class:

```python
class Provider(ABC):
    @abstractmethod
    def entity_definitions(self) -> list[EntityDefinitionSpec]:
        """Return entity definitions this provider can create"""
        pass

    @abstractmethod
    def reconcile(self, client: AuthenticatedClient) -> GraphMutations:
        """Reconcile entities with current graph state"""
        pass
```

### Common Components

Each molecule typically includes:
- **Provider**: Main reconciliation logic
- **Config**: Pydantic configuration models
- **Client**: API client for external system (where applicable)
- **Types**: Entity and relationship definitions
- **README**: Comprehensive documentation

### Configuration Structure

Molecules follow a consistent configuration pattern:

```yaml
discovery:
  api_base_url: https://api.devgraph.ai
  environment: <uuid>
  opaque_token: <token>
  molecules:
    - name: molecule-name
      type: molecule.type.identifier
      every: 300  # Reconciliation interval in seconds
      config:
        namespace: default
        # Molecule-specific configuration
```

**📖 See [CONFIGURATION.md](../../../CONFIGURATION.md) for detailed configuration schemas for all molecules.**

## Key Features

### Field-Selected Relations
Many molecules use field-selected relations to create intelligent connections between entities based on matching field values:

```python
# Example: Link Argo applications to GitHub repositories
repo_relation = ApplicationUsesRepositoryRelation.with_target_selector(
    relation="USES",
    source=app_entity.reference,
    target_selector=f"spec.url={repo_url}",
    target_kind="GitHubRepository"
)
```

### Error Handling
All molecules implement robust error handling:
- Graceful degradation on individual entity failures
- Empty mutations returned on critical failures to prevent partial state
- Comprehensive logging for debugging

### Pagination Support
Molecules handle large data sets efficiently:
- Paginated API requests where supported
- Configurable page sizes
- Memory-efficient processing

## Development Guidelines

### Creating a New Molecule

1. **Directory Structure**
   ```
   molecules/
   └── new-molecule/
       ├── __init__.py
       ├── README.md
       ├── provider.py
       ├── config.py
       ├── client.py (if needed)
       └── types/
           ├── __init__.py
           ├── relations.py
           └── v1_entity_type.py
   ```

2. **Implementation Steps**
   - Extend the `Provider` base class
   - Define configuration models with Pydantic
   - Implement entity type definitions
   - Create API client if needed
   - Add comprehensive docstrings
   - Write detailed README documentation

3. **Best Practices**
   - Use type hints throughout
   - Implement proper error handling
   - Add structured logging
   - Support field-selected relations where appropriate
   - Follow existing naming conventions

### Configuration Validation
Use Pydantic models for configuration validation:

```python
class MoleculeConfig(BaseModel):
    namespace: str = "default"
    api_url: str
    token: str = Field(..., description="Authentication token")
    selectors: List[SelectorConfig] = []
```

### Testing
Each molecule should include:
- Unit tests for configuration validation
- Mock API client tests
- Integration tests with test fixtures
- Error condition testing

## Common Patterns

### Entity Creation
```python
entity = EntityClass(
    metadata=EntityMetadata(
        name=entity_name,
        namespace=self.config.namespace,
        labels={"key": "value"}
    ),
    spec=EntitySpecClass(
        # Entity-specific fields
    )
)
```

### Relationship Creation
```python
relation = RelationClass(
    namespace=self.config.namespace,
    source=source_entity.reference,
    target=target_entity.reference
)
```

### API Client Pattern
```python
class MoleculeClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token

    def request(self, method, endpoint, **kwargs):
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.token}"
        # Implementation
```

## Deployment

### Configuration Management
- Use environment variables for sensitive data (tokens, passwords)
- Provide reasonable defaults where possible
- Document all configuration options

### Monitoring
- Implement structured logging with loguru
- Log entity counts and reconciliation metrics
- Include timing information for performance monitoring

### Security
- Never log sensitive information (tokens, passwords)
- Use read-only credentials where possible
- Implement proper error handling to avoid information leakage

## Contributing

When contributing new molecules or improvements:

1. Follow the established patterns and conventions
2. Add comprehensive docstrings and README documentation
3. Include appropriate error handling and logging
4. Test with various configuration scenarios
5. Consider backward compatibility for configuration changes

## Troubleshooting

### Common Issues

- **Authentication Failures**: Verify tokens and credentials
- **Connection Timeouts**: Check network connectivity and firewall rules
- **Rate Limiting**: Implement appropriate delays and retry logic
- **Memory Usage**: Use pagination for large data sets

### Debugging

Enable debug logging to see detailed operation traces:
```python
from loguru import logger
logger.add(sys.stdout, level="DEBUG")
```

Review the individual molecule READMEs for specific troubleshooting guidance.