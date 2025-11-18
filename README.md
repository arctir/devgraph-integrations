# Devgraph Integrations

[![CI](https://github.com/arctir/devgraph-integrations/actions/workflows/ci.yml/badge.svg)](https://github.com/arctir/devgraph-integrations/actions/workflows/ci.yml)
[![DCO](https://github.com/arctir/devgraph-integrations/actions/workflows/dco.yml/badge.svg)](https://github.com/arctir/devgraph-integrations/actions/workflows/dco.yml)
[![codecov](https://codecov.io/gh/arctir/devgraph-integrations/branch/main/graph/badge.svg)](https://codecov.io/gh/arctir/devgraph-integrations)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)

Entity discovery and synchronization framework for [Devgraph](https://devgraph.ai).

Devgraph Integrations is an open-source framework for discovering and synchronizing entities from external systems into the Devgraph ontology. It provides a plugin-based architecture for building providers that can discover entities from various sources like GitHub, GitLab, Jira, Kubernetes, and more.

## Features

- **Plugin-based architecture** - Easily extensible provider system
- **Automatic reconciliation** - Keep your graph in sync with external systems
- **Bulk operations** - Efficient entity and relation creation
- **Field selectors** - Dynamic relation resolution based on entity fields
- **Version management** - Built-in config versioning and migrations
- **Scheduling** - Configurable discovery intervals per provider
- **Meta types** - Automatic entity type classification

## Installation

```bash
pip install devgraph-integrations
```

### With MCP support

```bash
pip install devgraph-integrations[mcp]
```

## Quick Start

### Configuration

Create a `config.yaml` file:

```yaml
discovery:
  api_base_url: "https://api.devgraph.ai"
  environment: "your-environment-id"
  opaque_token: "your-api-token"
  molecules:
    - name: "github-org"
      type: "github.molecules.devgraph.ai"
      every: 300  # seconds
      config:
        namespace: "default"
        authentication:
          type: pat
          token: "ghp_..."
        selectors:
          - organization: "your-org"
```

**📖 See [CONFIGURATION.md](./CONFIGURATION.md) for complete configuration documentation for all available molecules.**

### Running Discovery

```bash
devgraph-integrations --config config.yaml
```

Or as a one-shot operation:

```bash
devgraph-integrations --config config.yaml --oneshot
```

### Docker

```bash
docker build -t devgraph-integrations .
docker run -v $(pwd)/config.yaml:/app/config.yaml devgraph-integrations
```

## Built-in Providers

Devgraph Integrations includes providers for:

- **GitHub** - Repositories, teams, users, pull requests
- **GitLab** - Projects, groups, merge requests
- **Jira** - Issues, projects, boards
- **Kubernetes/Argo** - Applications, deployments, namespaces
- **LDAP** - Users, groups, organizational structure
- **Docker** - Images, containers, registries
- **Vercel** - Projects, deployments
- **FOSSA** - Dependencies, licenses, vulnerabilities
- **File** - Static entity definitions from YAML files

## Creating Custom Providers

```python
from devgraph_integrations import Provider, GraphMutations
from devgraph_ai_api_client import AuthenticatedClient

class MyProvider(Provider):
    _config_cls = MyProviderConfig

    def entity_definitions(self):
        return [MyEntityDefinition()]

    def reconcile(self, client: AuthenticatedClient) -> GraphMutations:
        # Discover entities from your system
        entities = self.discover_entities()
        relations = self.discover_relations()

        return GraphMutations(
            create_entities=entities,
            delete_entities=[],
            create_relations=relations,
            delete_relations=[]
        )
```

Register your provider via plugin system in `pyproject.toml`:

```toml
[tool.poetry.plugins."devgraph.discovery.providers"]
"my-provider.providers.devgraph.ai" = "my_package.provider:MyProvider"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DiscoveryProcessor                        │
│  - Manages provider lifecycle                               │
│  - Schedules reconciliation loops                           │
│  - Handles API communication                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Provider (Base Class)                     │
│  - entity_definitions() - Define entity schemas             │
│  - reconcile() - Discover and sync entities                 │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   GitHub Provider       GitLab Provider      Custom Provider
```

## Development

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=devgraph_integrations

# Format code
poetry run black .
poetry run isort .

# Type checking
poetry run mypy devgraph_integrations
```

### Commit Message Format

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`

Scopes: `fossa`, `github`, `gitlab`, `docker`, `argo`, `file`, `ldap`, `jira`, `vercel`, `grafana`, `core`, `config`, `cli`, `tests`

Examples:
```
feat(fossa): add relation creation for repositories
fix(github): handle rate limiting errors
docs(tests): update testing framework documentation
test(gitlab): add selector filtering tests
```

## License

Apache License 2.0

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

**Requirements:**
- All commits must be **signed off** with `-s` flag ([DCO](DCO))
- **GPG signing** strongly encouraged
- Follow **conventional commits** format
- Include **tests** for new features

```bash
# Example signed commit
git commit -s -m "feat(fossa): add webhook support"
```

## Documentation

Full documentation available at [docs.devgraph.ai](https://docs.devgraph.ai)

## Support

- GitHub Issues: [github.com/arctir/devgraph-integrations/issues](https://github.com/arctir/devgraph-integrations/issues)
- Documentation: [docs.devgraph.ai](https://docs.devgraph.ai)
