# Molecule Configuration Guide

This guide documents the configuration schema for all available molecules in devgraph-integrations.

## Configuration Structure

Molecules are configured in YAML format with the following top-level structure:

```yaml
discovery:
  api_base_url: https://api.devgraph.ai
  environment: <uuid>
  opaque_token: <token>
  molecules:
    - name: molecule-instance-name
      type: molecule.type.identifier
      every: 60  # Discovery interval in seconds
      config:
        # Molecule-specific configuration
```

## Available Molecules

### GitHub

Discovers GitHub repositories and hosting services.

**Type:** `github.molecules.devgraph.ai`

**Configuration:**

```yaml
- name: my-github
  type: github.molecules.devgraph.ai
  every: 300
  config:
    # Optional: Custom GitHub instance
    base_url: https://github.com  # Default
    api_url: https://api.github.com  # Default

    # Required: Authentication (choose one)
    authentication:
      # Option 1: Personal Access Token
      type: pat
      token: ghp_yourTokenHere

      # Option 2: GitHub App (higher rate limits)
      # type: app
      # app_id: 123456
      # app_private_key: |
      #   -----BEGIN RSA PRIVATE KEY-----
      #   ...
      #   -----END RSA PRIVATE KEY-----
      # installation_id: 789012

    # Repository selectors
    selectors:
      - organization: myorg
        repo_name: ".*"  # Optional regex pattern (default: .*)
        graph_files:  # Optional (default: [.devgraph.yaml])
          - .devgraph.yaml
          - .devgraph/*.yaml
```

**Required Permissions (PAT):**
- `repo` (read repositories)
- `read:org` (read organization information)

**Entities Created:**
- `GitHubRepository`
- `GitHubHostingService`

---

### GitLab

Discovers GitLab projects and hosting services.

**Type:** `gitlab.molecules.devgraph.ai`

**Configuration:**

```yaml
- name: my-gitlab
  type: gitlab.molecules.devgraph.ai
  every: 300
  config:
    # Optional: Custom GitLab instance
    base_url: https://gitlab.com  # Default
    api_url: https://gitlab.com/api/v4  # Default

    # Required: Personal Access Token
    token: glpat_yourTokenHere

    # Project selectors
    selectors:
      - group: mygroup
        project_name: ".*"  # Optional regex pattern (default: .*)
        graph_files:  # Optional (default: [.devgraph.yaml])
          - .devgraph.yaml
```

**Required Permissions:**
- `read_api` (read-only access to API)

**Entities Created:**
- `GitLabProject`
- `GitLabHostingService`

---

### Argo CD

Discovers Argo CD applications and projects.

**Type:** `argo.molecules.devgraph.ai`

**Configuration:**

```yaml
- name: my-argo
  type: argo.molecules.devgraph.ai
  every: 300
  config:
    # Required
    api_url: https://argocd.example.com/api/v1/
    token: eyJ...  # Argo CD auth token

    # Optional
    namespace: default
```

**Required Permissions:**
- Read access to applications and projects

**Entities Created:**
- `ArgoInstance`
- `ArgoProject`
- `ArgoApplication`

**Relationships:**
- `ArgoApplication` USES `GitHubRepository` (via field selector on spec.sources[].repoURL)

---

### Vercel

Discovers Vercel teams, projects, and deployments.

**Type:** `vercel.molecules.devgraph.ai`

**Configuration:**

```yaml
- name: my-vercel
  type: vercel.molecules.devgraph.ai
  every: 300
  config:
    # Required
    token: your_vercel_token
    team_id: team_xxx  # Optional: specific team ID

    # Optional
    namespace: default

    # Optional: Filter projects
    selectors:
      - project_name_pattern: ".*"  # Regex pattern
```

**Required Permissions:**
- Read access to teams, projects, and deployments

**Entities Created:**
- `VercelTeam`
- `VercelProject`
- `VercelDeployment`

---

### Docker Registry

Discovers Docker images from container registries.

**Type:** `docker.molecules.devgraph.ai`

**Configuration:**

```yaml
- name: my-docker
  type: docker.molecules.devgraph.ai
  every: 300
  config:
    # Required
    registry_type: ghcr  # or: docker_hub, ecr, gcr, acr
    api_url: https://ghcr.io/

    # Authentication (depends on registry type)
    username: myuser  # For GHCR, Docker Hub
    token: ghp_token  # For GHCR: GitHub PAT, Docker Hub: access token

    # Optional
    namespace: default

    # Repository selectors
    selectors:
      - namespace_pattern: myorg  # Registry namespace/org
        repository_pattern: "^myapp.*"  # Regex for repo names
        max_tags: 10  # Limit tags per repo (default: 10)
        exclude_tags:  # Optional: exclude patterns
          - ".*-dev"
          - ".*-test"
          - latest
```

**Registry-Specific Notes:**
- **GHCR**: Use GitHub PAT with `read:packages` scope
- **Docker Hub**: Use access token with read permissions
- **ECR/GCR/ACR**: Configure credentials per cloud provider

**Entities Created:**
- `DockerRegistry`
- `DockerRepository`
- `DockerImage`

**Relationships:**
- `DockerImage` BUILT_FROM `GitHubRepository` (via org.opencontainers.image.source label)

---

### FOSSA

Discovers FOSSA projects and their dependencies.

**Type:** `fossa.molecules.devgraph.ai`

**Configuration:**

```yaml
- name: my-fossa
  type: fossa.molecules.devgraph.ai
  every: 3600  # FOSSA data changes less frequently
  config:
    # Required
    token: your_fossa_api_token

    # Optional
    base_url: https://app.fossa.com/api  # Default
    filter_title: "my-project"  # Optional: filter by project title
    namespace: default
```

**Required Permissions:**
- Read access to projects and issues

**Entities Created:**
- `FOSSAProject`
- `FOSSAIssue`

---

### LDAP

Discovers users, groups, and organizational units from LDAP directories.

**Type:** `ldap.molecules.devgraph.ai`

**Configuration:**

```yaml
- name: my-ldap
  type: ldap.molecules.devgraph.ai
  every: 3600
  config:
    # Required
    server_uri: ldap://ldap.example.com
    base_dn: dc=example,dc=com

    # Authentication (optional for anonymous bind)
    bind_dn: cn=readonly,dc=example,dc=com
    bind_password: password

    # Optional
    namespace: default
    use_tls: true  # Default: false

    # Selectors for users and groups
    selectors:
      - user_filter: "(objectClass=inetOrgPerson)"
        group_filter: "(objectClass=groupOfNames)"
        ou_filter: "(objectClass=organizationalUnit)"
```

**Entities Created:**
- `LDAPUser`
- `LDAPGroup`
- `LDAPOrganizationalUnit`

**Relationships:**
- `LDAPUser` MEMBER_OF `LDAPGroup`
- `LDAPGroup` MEMBER_OF `LDAPGroup` (nested groups)

---

### File-Based

Discovers entities and relationships from local YAML files.

**Type:** `file.molecules.devgraph.ai`

**Configuration:**

```yaml
- name: local-files
  type: file.molecules.devgraph.ai
  every: 60
  config:
    namespace: default
    base_path: /path/to/project
    paths:
      - .devgraph.yaml
      - configs/**/*.yaml  # Supports glob patterns
```

**File Format:**

Files should contain entity definitions in YAML format:

```yaml
apiVersion: entities.devgraph.ai/v1
kind: Service
metadata:
  name: my-service
  namespace: default
spec:
  display_name: My Service
  description: Service description
```

**Entities Created:**
- Any entity type defined in the files

---

### Meta

Creates meta-type entities (Team, Workstream) for organizing other entities.

**Type:** `meta.molecules.devgraph.ai`

**Configuration:**

```yaml
- name: meta
  type: meta.molecules.devgraph.ai
  every: 3600
  config:
    namespace: default
```

**Note:** This molecule automatically creates meta-type entities based on entity definitions that specify a `meta_type` field.

**Entities Created:**
- `Team` (meta-type for organizational entities)
- `Workstream` (meta-type for project/initiative entities)

---

### Grafana

Discovers Grafana dashboards and data sources.

**Type:** `grafana.molecules.devgraph.ai`

**Configuration:**

```yaml
- name: my-grafana
  type: grafana.molecules.devgraph.ai
  every: 300
  config:
    # Required
    api_url: https://grafana.example.com
    token: your_grafana_api_token

    # Optional
    namespace: default
```

**Required Permissions:**
- Read access to dashboards and data sources

**Entities Created:**
- `GrafanaDashboard`
- `GrafanaDataSource`

---

## Common Configuration Patterns

### Namespace

All molecules support a `namespace` field (default: `default`) to organize entities:

```yaml
config:
  namespace: production  # Group entities by environment
```

### Discovery Interval

The `every` field controls how often the molecule runs (in seconds):

```yaml
every: 300  # Run every 5 minutes
every: 3600  # Run every hour
```

**Recommendations:**
- Fast-changing data (deployments): 60-300 seconds
- Slow-changing data (repositories, users): 1800-3600 seconds
- Expensive APIs (FOSSA): 3600+ seconds

### Selectors

Many molecules use selectors to filter discovered entities:

```yaml
selectors:
  - organization: myorg
    repo_name: "^api-.*"  # Regex pattern
  - organization: myorg2
    repo_name: ".*-service$"
```

Multiple selectors are OR'd together (discovers entities matching any selector).

### Authentication

**Token Storage:**
- Use environment variables: `token: ${GITHUB_TOKEN}`
- Use secret management: External secret stores via stevedore extensions
- Never commit tokens to version control

**Token Permissions:**
- Use read-only tokens whenever possible
- Grant minimum required scopes
- Rotate tokens regularly

## Troubleshooting

### Validation Errors

If you see "Field required" errors, check:
1. Field name matches the schema (e.g., `token` not `api_token`)
2. Required nested objects are present (e.g., `authentication.type`)
3. Discriminated unions have the correct type field

### Authentication Failures

If molecules fail to authenticate:
1. Verify token is valid and not expired
2. Check token has required permissions/scopes
3. For enterprise instances, verify URLs are correct
4. Check network connectivity to API endpoints

### Rate Limiting

If you hit API rate limits:
1. Increase the `every` interval
2. Use GitHub App authentication (higher limits)
3. Reduce the scope of selectors
4. Add caching if supported by the molecule

## Advanced Configuration

### Extending Configuration

Molecule configuration can be extended via stevedore plugins to add:
- Encrypted secret fields
- API-based configuration fetching
- Custom validation logic
- Additional authentication methods

See `EXTENSIONS.md` for details on creating configuration extensions.

### Environment Variables

Configuration supports environment variable substitution:

```yaml
config:
  token: ${GITHUB_TOKEN}  # Reads from environment
  api_url: ${API_URL:-https://api.github.com}  # With default value
```

### Multiple Instances

You can configure multiple instances of the same molecule type:

```yaml
molecules:
  - name: org1-github
    type: github.molecules.devgraph.ai
    config:
      # Config for org1

  - name: org2-github
    type: github.molecules.devgraph.ai
    config:
      # Config for org2
```

Each instance runs independently with its own schedule and configuration.
