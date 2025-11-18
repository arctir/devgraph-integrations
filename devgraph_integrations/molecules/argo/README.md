# Argo CD Molecule

The Argo CD molecule provides integration with Argo CD's API to discover and manage Argo CD instances, projects, and applications as entities in the Devgraph system.

## Overview

This molecule connects to the Argo CD API to discover projects and applications within an Argo CD instance, creating corresponding entities and relationships in the Devgraph. It supports field-selected relations to link applications with their source repositories.

## Entities Created

- **Argo Instance**: Represents the Argo CD instance itself
- **Argo Project**: Represents Argo CD projects
- **Argo Application**: Represents individual applications with their configurations

## Configuration

The Argo CD provider is configured using the `ArgoProviderConfig` class:

```yaml
providers:
  - name: argo-provider
    type: argo
    every: 180  # Run every 3 minutes
    config:
      namespace: default
      api_base_url: https://argocd.example.com/api/v1/
      token: ${ARGO_TOKEN}
```

### Configuration Options

- `namespace`: Kubernetes-style namespace for created entities
- `api_base_url`: Base URL for Argo CD API endpoints
- `token`: Authentication token for Argo CD API access

## Authentication

The provider requires an Argo CD authentication token:

1. Login to your Argo CD instance
2. Generate a new token via CLI: `argocd account generate-token`
3. Or create a project token in the Argo CD UI
4. Set the token in your configuration or environment variable

## Relationships

The provider creates the following relationships:

- **Project → Belongs To → Instance**: Links projects to the Argo CD instance
- **Application → Belongs To → Project**: Links applications to their projects
- **Application → Uses → Repository**: Field-selected relation linking apps to their source repositories

## Field-Selected Relations

The provider creates intelligent relationships between Argo CD applications and their source repositories by analyzing the `spec.sources[].repoURL` field and creating field-selected relations that target GitHub repositories with matching URLs.

## Example Entities

### Argo Application Entity
```yaml
apiVersion: entities.devgraph.io/v1
kind: ArgoApplication
metadata:
  name: my-app
  namespace: default
spec:
  name: my-app
```

### Argo Project Entity
```yaml
apiVersion: entities.devgraph.io/v1
kind: ArgoProject
metadata:
  name: default
  namespace: default
spec:
  name: default
```

### Argo Instance Entity
```yaml
apiVersion: entities.devgraph.io/v1
kind: ArgoInstance
metadata:
  name: argo
  namespace: default
spec:
  api_url: https://argocd.example.com/api/v1/
```

## Error Handling

The provider implements comprehensive error handling:

- Returns empty mutations on reconciliation failure to prevent partial state
- Logs detailed error messages for debugging
- Continues processing other entities if individual entities fail

## Files

- `provider.py`: Main provider implementation
- `config.py`: Configuration models
- `client.py`: Argo CD API client
- `types/`: Entity type definitions
- `types/relations.py`: Relationship definitions

## Dependencies

- `requests`: HTTP client for API calls
- `loguru`: Logging
- `pydantic`: Configuration validation