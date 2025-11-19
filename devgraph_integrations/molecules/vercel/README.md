# Vercel Molecule

The Vercel molecule provides integration with Vercel's API to discover and manage teams, projects, and deployments as entities in the Devgraph system.

## Overview

This molecule connects to the Vercel API to discover teams, projects, and deployments within specified selectors, creating corresponding entities and relationships in the Devgraph. It supports field-selected relations to link projects with their source repositories.

## Entities Created

- **Vercel Team**: Represents Vercel teams/organizations
- **Vercel Project**: Represents individual projects with metadata
- **Vercel Deployment**: Represents recent deployments (limited to 5 most recent)

## Configuration

The Vercel provider is configured using the `VercelProviderConfig` class:

```yaml
providers:
  - name: vercel-provider
    type: vercel
    every: 300  # Run every 5 minutes
    config:
      namespace: default
      api_base_url: https://api.vercel.com
      token: ${VERCEL_TOKEN}
      selectors:
        - team_id: team_abc123
          project_name_pattern: "frontend-.*"
        - team_id: null  # Personal projects
          project_name_pattern: ".*"
```

### Configuration Options

- `namespace`: Kubernetes-style namespace for created entities
- `api_base_url`: Base URL for Vercel API (default: https://api.vercel.com)
- `token`: Vercel authentication token
- `selectors`: List of project selection criteria
  - `team_id`: Vercel team ID to scan (null for personal projects)
  - `project_name_pattern`: Regex pattern for project names (default: matches all)

## Authentication

The provider requires a Vercel authentication token:

1. Go to Vercel Account Settings → Tokens
2. Create a new token with appropriate scope
3. Set the token in your configuration or environment variable

## Relationships

The provider creates the following relationships:

- **Project → Belongs To → Team**: Links projects to their teams
- **Deployment → Belongs To → Project**: Links deployments to their projects
- **Project → Uses → Repository**: Field-selected relation linking projects to their source repositories

## Field-Selected Relations

The provider creates intelligent relationships between Vercel projects and their source repositories by analyzing the `link.type` and repository information, creating field-selected relations that target GitHub repositories with matching URLs.

## Example Entities

### Vercel Project Entity
```yaml
apiVersion: entities.devgraph.io/v1
kind: VercelProject
metadata:
  name: my-frontend
  namespace: default
  labels:
    project_id: prj_abc123
    team_id: team_def456
spec:
  name: my-frontend
  id: prj_abc123
  framework: nextjs
  url: https://my-frontend.vercel.app
  description: My awesome frontend
  team_id: team_def456
  created_at: "2023-01-01T00:00:00Z"
  updated_at: "2023-12-01T00:00:00Z"
```

### Vercel Team Entity
```yaml
apiVersion: entities.devgraph.io/v1
kind: VercelTeam
metadata:
  name: my-team
  namespace: default
  labels:
    team_id: team_def456
spec:
  id: team_def456
  slug: my-team
  name: My Team
  avatar: https://avatar.url
  created_at: "2022-01-01T00:00:00Z"
```

### Vercel Deployment Entity
```yaml
apiVersion: entities.devgraph.io/v1
kind: VercelDeployment
metadata:
  name: my-frontend-abc12345
  namespace: default
  labels:
    project_id: prj_abc123
    deployment_uid: dpl_abc12345
    state: READY
spec:
  uid: dpl_abc12345
  name: my-frontend
  url: https://my-frontend-abc12345.vercel.app
  project_id: prj_abc123
  state: READY
  type: LAMBDA
  target: production
  created_at: "2023-12-01T12:00:00Z"
  ready: true
```

## Error Handling

The provider implements comprehensive error handling:

- Returns empty mutations on reconciliation failure to prevent partial state
- Logs detailed error messages for debugging
- Continues processing other entities if individual entities fail
- Limits deployment discovery to 5 most recent to prevent overwhelming the system

## Files

- `provider.py`: Main provider implementation
- `config.py`: Configuration models
- `client.py`: Vercel API client
- `types/`: Entity type definitions
- `types/relations.py`: Relationship definitions

## Dependencies

- `requests`: HTTP client for API calls
- `loguru`: Logging
- `pydantic`: Configuration validation
