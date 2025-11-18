# GitHub Molecule

The GitHub molecule provides integration with GitHub's API to discover and manage repositories and hosting services as entities in the Devgraph system.

## Overview

This molecule connects to the GitHub API to discover repositories within specified organizations and creates corresponding entities and relationships in the Devgraph. It supports filtering repositories by name patterns and organizing them under hosting service entities.

## Entities Created

- **GitHub Hosting Service**: Represents the GitHub platform itself
- **GitHub Repository**: Represents individual repositories with metadata

## Configuration

The GitHub provider is configured using the `GithubProviderConfig` class:

```yaml
providers:
  - name: github-provider
    type: github
    every: 300  # Run every 5 minutes
    config:
      namespace: default
      base_url: https://github.com
      api_url: https://api.github.com
      token: ${GITHUB_TOKEN}
      selectors:
        - organization: myorg
          repo_name: "service-.*"  # Regex pattern
          graph_files:
            - .devgraph.yaml
```

### Configuration Options

- `namespace`: Kubernetes-style namespace for created entities
- `base_url`: Base URL for GitHub web interface (default: https://github.com)
- `api_url`: GitHub API base URL (default: https://api.github.com)
- `token`: GitHub personal access token for authentication
- `selectors`: List of organization and repository selection criteria
  - `organization`: GitHub organization name to scan
  - `repo_name`: Regex pattern for repository names (default: matches all)
  - `graph_files`: List of file paths to read for graph definitions (entities and relationships)

## Authentication

The provider requires a GitHub personal access token with appropriate permissions:

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a new token with `repo` scope for private repositories, or `public_repo` for public only
3. Set the token in your configuration or environment variable

## Relationships

The provider creates the following relationships:

- **Repository → Hosted By → Hosting Service**: Links repositories to the GitHub hosting service

## Example Entities

### GitHub Repository Entity
```yaml
apiVersion: entities.devgraph.io/v1
kind: GithubRepository
metadata:
  name: my-service
  namespace: default
  labels:
    organization: myorg
spec:
  organization: myorg
  name: my-service
  url: https://github.com/myorg/my-service
  description: My awesome service
```

### GitHub Hosting Service Entity
```yaml
apiVersion: entities.devgraph.io/v1
kind: GithubHostingService
metadata:
  name: github
  namespace: default
  labels:
    organization: github
spec:
  api_url: https://api.github.com
```

## Files

- `provider.py`: Main provider implementation
- `config.py`: Configuration models
- `types/`: Entity type definitions
- `types/relations.py`: Relationship definitions

## Dependencies

- `PyGithub`: GitHub API client library
- `requests`: HTTP client
- `loguru`: Logging