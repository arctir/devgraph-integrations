# GitHub

Discover GitHub repositories, hosting services, and repository metadata.

## Overview

The GitHub molecule discovers repositories from GitHub organizations and creates entity relationships for your Devgraph. It supports both personal access token (PAT) and GitHub App authentication.

## Capabilities

- **Discovery**: Scans organizations for repositories and metadata
- **MCP**: Provides Model Context Protocol server for AI integrations

## Entity Types

| Entity Type | Description |
|-------------|-------------|
| `GitHubRepository` | A GitHub repository with metadata |
| `GitHubHostingService` | The GitHub instance (github.com or enterprise) |

## Relation Types

| Relation Type | Description |
|---------------|-------------|
| `GitHubRepositoryHostedBy` | Links repositories to their hosting service |

## Authentication

The GitHub molecule supports two authentication methods:

### Personal Access Token (PAT)

```yaml
authentication:
  type: pat
  token: ghp_xxxxxxxxxxxx
```

Required scopes:
- `repo` (for private repositories)
- `read:org` (for organization access)

### GitHub App

```yaml
authentication:
  type: app
  app_id: 123456
  app_private_key: |
    -----BEGIN RSA PRIVATE KEY-----
    ...
    -----END RSA PRIVATE KEY-----
  installation_id: 12345678
```

## Configuration

```yaml
discovery:
  molecules:
    - name: github-main
      type: github
      every: 300
      config:
        base_url: https://github.com
        api_url: https://api.github.com
        authentication:
          type: pat
          token: ${GITHUB_TOKEN}
        selectors:
          - organization: my-org
            repo_name: ".*"
            graph_files:
              - .devgraph.yaml
```

### Configuration Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `base_url` | string | `https://github.com` | Base URL for GitHub web interface |
| `api_url` | string | `https://api.github.com` | GitHub API base URL |
| `authentication` | object | required | Authentication configuration (PAT or App) |
| `selectors` | array | `[]` | Repository selection criteria |

### Selector Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `organization` | string | required | GitHub organization name to scan |
| `repo_name` | string | `.*` | Regex pattern for repository names |
| `graph_files` | array | `[".devgraph.yaml"]` | File paths to read for graph definitions |

## GitHub Enterprise

For GitHub Enterprise Server, update the URLs:

```yaml
config:
  base_url: https://github.mycompany.com
  api_url: https://github.mycompany.com/api/v3
  authentication:
    type: pat
    token: ${GITHUB_TOKEN}
```

## Rate Limiting

GitHub API has rate limits:
- PAT: 5,000 requests/hour
- GitHub App: 15,000 requests/hour

The GitHub App authentication method provides higher rate limits and is recommended for large organizations.
