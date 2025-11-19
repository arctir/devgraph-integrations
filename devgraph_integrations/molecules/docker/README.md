# Docker Registry Molecule

The Docker Registry molecule provides integration with Docker registries to discover and manage container images, repositories, and registry metadata as entities in Devgraph.

## Overview

This molecule connects to various Docker registries (Docker Hub, AWS ECR, Google GCR, Azure ACR, or private registries) to discover:

- **Docker Registries** - Registry instances that host container images
- **Docker Repositories** - Container image repositories within registries
- **Docker Images** - Specific tagged versions of container images
- **Docker Manifests** - Image manifests containing metadata and layer information

## Configuration

### Basic Configuration

```yaml
discovery:
  providers:
    - name: "docker-hub"
      type: "docker"
      config:
        registry_type: "docker-hub"
        api_url: "https://registry-1.docker.io"
        # Authentication (optional for public repos)
        username: "your-username"
        password: "your-password"
        # Or use token
        token: "your-registry-token"

        # Discovery settings
        discover_vulnerabilities: false

        # Repository selection
        selectors:
          - namespace_pattern: "library"  # Official images
            repository_pattern: "^(nginx|ubuntu|postgres)$"
            max_tags: 5
            exclude_tags: [".*-rc.*", ".*-beta.*"]
```

### Registry Types

The molecule supports different registry types with appropriate authentication:

#### Docker Hub
```yaml
config:
  registry_type: "docker-hub"
  api_url: "https://registry-1.docker.io"
  username: "your-username"
  password: "your-password"
```

#### AWS ECR
```yaml
config:
  registry_type: "ecr"
  api_url: "https://123456789.dkr.ecr.us-west-2.amazonaws.com"
  token: "your-ecr-token"  # AWS CLI token
```

#### Google GCR
```yaml
config:
  registry_type: "gcr"
  api_url: "https://gcr.io"
  token: "your-gcr-token"  # gcloud auth token
```

#### Azure ACR
```yaml
config:
  registry_type: "acr"
  api_url: "https://myregistry.azurecr.io"
  username: "your-username"
  password: "your-password"
```

#### GitHub Container Registry (GHCR)

**Option 1: Username + Token (Recommended)**
```yaml
config:
  registry_type: "ghcr"
  api_url: "https://ghcr.io"
  username: "your-github-username"
  token: "ghp_your_classic_token"  # Classic PAT as token field
```

**Option 2: Username + Password**
```yaml
config:
  registry_type: "ghcr"
  api_url: "https://ghcr.io"
  username: "your-github-username"
  password: "ghp_your_classic_token"  # Classic PAT as password field
```

**Required Token Scopes:**
- `read:packages` - Required for reading container images and metadata
- `write:packages` - If you need to push images (includes read:packages)
- `delete:packages` - If you need to delete packages (requires read:packages)

**Important:** GHCR only supports **Classic Personal Access Tokens**, not fine-grained tokens.

#### Private Registry
```yaml
config:
  registry_type: "private"
  api_url: "https://my-private-registry.com"
  username: "admin"
  password: "secret-password"
```

### Selector Configuration

Fine-tune which repositories and images are discovered:

```yaml
selectors:
  - namespace_pattern: "myorg.*"      # Match namespaces starting with "myorg"
    repository_pattern: ".*api.*"     # Match repositories containing "api"
    include_tags: ["latest", "stable"] # Only these tags
    max_tags: 10                      # Limit tags per repository

  - namespace_pattern: "library"      # Official Docker images
    repository_pattern: "^(node|python|golang)$"
    exclude_tags: [".*-alpine.*"]     # Exclude Alpine variants
    max_tags: 3
```

### Configuration Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `api_url` | string | `https://registry-1.docker.io` | Registry API base URL |
| `registry_type` | string | `docker-hub` | Registry type (`docker-hub`, `ecr`, `gcr`, `acr`, `ghcr`, `private`) |
| `username` | string | - | Username for basic authentication |
| `password` | string | - | Password for basic authentication |
| `token` | string | - | Registry authentication token |
| `namespace` | string | `default` | Kubernetes namespace for entities |
| `timeout` | int | `30` | Request timeout in seconds |
| `discover_vulnerabilities` | bool | `false` | Whether to discover vulnerability data |
| `selectors` | array | `[{}]` | Repository selection criteria |

#### Selector Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `namespace_pattern` | string | `.*` | Regex pattern for repository namespaces |
| `repository_pattern` | string | `.*` | Regex pattern for repository names |
| `include_tags` | array | - | Specific tags to include |
| `exclude_tags` | array | - | Tag patterns to exclude |
| `max_tags` | int | `10` | Maximum tags per repository |

## Discovered Entities

### DockerRegistry

Represents a Docker registry instance.

**Spec Fields:**
- `name` - Human-readable registry name
- `registry_type` - Registry type (docker-hub, ecr, etc.)
- `url` - Registry base URL
- `description` - Registry description
- `version` - API version
- `public` - Whether registry is public

**Labels:**
- `devgraph.ai/provider: docker`
- `devgraph.ai/registry-type: <type>`

### DockerRepository

Represents a container image repository.

**Spec Fields:**
- `name` - Repository name (e.g., 'nginx')
- `full_name` - Full name with namespace (e.g., 'library/nginx')
- `namespace` - Repository namespace/organization
- `description` - Repository description
- `official` - Whether it's an official repository
- `automated` - Whether builds are automated
- `star_count` - Number of stars
- `pull_count` - Number of pulls
- `last_updated` - Last update timestamp
- `registry_url` - Parent registry URL

**Labels:**
- `devgraph.ai/provider: docker`
- `devgraph.ai/registry-type: <type>`
- `devgraph.ai/repository-name: <name>`

### DockerImage

Represents a specific tagged image version.

**Spec Fields:**
- `repository` - Parent repository name
- `tag` - Image tag (e.g., 'latest', 'v1.0.0')
- `digest` - SHA256 digest
- `size` - Image size in bytes
- `architecture` - Target architecture
- `os` - Target OS
- `created` - Creation timestamp
- `last_updated` - Last update timestamp
- `labels` - Image labels/metadata
- `layers` - Number of layers
- `vulnerabilities` - Vulnerability scan results
- `registry_url` - Parent registry URL

**Labels:**
- `devgraph.ai/provider: docker`
- `devgraph.ai/registry-type: <type>`
- `devgraph.ai/repository-name: <name>`
- `devgraph.ai/image-tag: <tag>`

### DockerManifest

Represents image manifest metadata.

**Spec Fields:**
- `repository` - Parent repository name
- `digest` - Manifest digest
- `media_type` - Manifest media type
- `schema_version` - Manifest schema version
- `architecture` - Target architecture
- `os` - Target OS
- `size` - Total image size
- `config_digest` - Configuration blob digest
- `layer_digests` - Layer digests
- `created` - Creation timestamp
- `registry_url` - Parent registry URL

**Labels:**
- `devgraph.ai/provider: docker`
- `devgraph.ai/registry-type: <type>`
- `devgraph.ai/repository-name: <name>`
- `devgraph.ai/manifest-digest: <digest>`

## Relationships

The Docker molecule creates the following relationships:

- **DockerRepository BELONGS_TO DockerRegistry** - Links repositories to their parent registry
- **DockerImage BELONGS_TO DockerRepository** - Links images to their parent repository
- **DockerImage USES DockerManifest** - Links images to their manifest metadata
- **DockerManifest BELONGS_TO DockerRepository** - Links manifests to their parent repository

## Use Cases

### Container Inventory Management
Track all container images across multiple registries to maintain an inventory of your containerized applications.

### Vulnerability Management
Discover container images and their metadata to support vulnerability scanning and compliance processes.

### Deployment Tracking
Link container images to deployment entities to track which versions are deployed where.

### License Compliance
Track container image metadata and labels to ensure license compliance across your container ecosystem.

### Registry Migration
Discover and catalog images before migrating between registries or consolidating registry instances.

## Security Considerations

### Authentication
- Store registry credentials securely using environment variables or secrets management
- Use registry-specific tokens when available instead of passwords
- Regularly rotate authentication credentials

### Registry Access
- Configure appropriate network access and firewall rules
- Use private registries for sensitive images
- Implement registry scanning for vulnerabilities

### Rate Limits
- Be aware of registry API rate limits, especially for Docker Hub
- Configure appropriate timeouts and retry policies
- Use authentication to get higher rate limits

## Examples

### Discover Official Docker Images
```yaml
- name: "docker-official"
  type: "docker"
  config:
    registry_type: "docker-hub"
    selectors:
      - namespace_pattern: "library"
        repository_pattern: "^(nginx|redis|postgres|mysql)$"
        max_tags: 3
        exclude_tags: [".*-rc.*"]
```

### Private Registry Discovery
```yaml
- name: "private-registry"
  type: "docker"
  config:
    registry_type: "private"
    api_url: "https://registry.company.com"
    username: "${REGISTRY_USERNAME}"
    password: "${REGISTRY_PASSWORD}"
    selectors:
      - namespace_pattern: "company.*"
        repository_pattern: ".*"
        max_tags: 5
```

### AWS ECR Discovery
```yaml
- name: "aws-ecr"
  type: "docker"
  config:
    registry_type: "ecr"
    api_url: "https://123456789.dkr.ecr.us-west-2.amazonaws.com"
    token: "${AWS_ECR_TOKEN}"
    selectors:
      - namespace_pattern: "production"
        repository_pattern: ".*api.*"
        include_tags: ["latest", "stable"]
```

### GitHub Container Registry (GHCR) Discovery
```yaml
- name: "github-packages"
  type: "docker"
  config:
    registry_type: "ghcr"
    api_url: "https://ghcr.io"
    username: "${GITHUB_USERNAME}"
    token: "${GITHUB_TOKEN}"  # Classic PAT with read:packages scope
    selectors:
      # GHCR requires explicit repository names (no catalog discovery)
      - namespace_pattern: "myorg"
        repository_pattern: "^(app-frontend|app-backend|shared-lib)$"
        max_tags: 10
        exclude_tags: [".*-dev.*", ".*-test.*"]
      - namespace_pattern: "myusername"
        repository_pattern: "^(personal-tool|demo-app)$"
        max_tags: 5
```

**GHCR-Specific Notes:**
- GHCR doesn't support the `/v2/_catalog` endpoint for security reasons
- You must specify exact repository names in `repository_pattern`
- Use patterns like `^(repo1|repo2|repo3)$` to specify multiple repositories
- The molecule will construct full repository names as `namespace/repository`

## Troubleshooting

### Authentication Issues
- Verify credentials are correct and have necessary permissions
- Check if registry supports the authentication method being used
- For Docker Hub, ensure you're using the correct registry URL

### GHCR 403 Forbidden Errors
If you're getting 403 errors with GitHub Container Registry:

1. **Use Classic Personal Access Token**: GHCR does not support fine-grained tokens
   - Go to: GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)
   - Generate new token with required scopes

2. **Required Token Scopes**:
   - **Minimum**: `read:packages` scope for reading container images
   - **Recommended**: `write:packages` scope (includes read access)
   - **Avoid**: Don't select `repo` scope unless absolutely necessary

3. **Quick Token Creation**: Use this direct link to create a token with only package scopes:
   ```
   https://github.com/settings/tokens/new?scopes=read:packages
   ```

4. **Verify Package Visibility**: Ensure the packages you're trying to access are:
   - Public, or
   - Private but your token has access to the repository/organization

5. **Test Authentication**:
   ```bash
   echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin
   ```

### GHCR Catalog Discovery Issues
If you see errors like "403 Client Error: Forbidden for url: https://ghcr.io/v2/_catalog":

1. **This is expected behavior**: GHCR doesn't support the catalog endpoint
2. **Configure explicit repositories**: You must specify exact repository names in selectors:
   ```yaml
   selectors:
     - namespace_pattern: "myorg"
       repository_pattern: "^(repo1|repo2|repo3)$"  # Explicit names
   ```
3. **Don't use wildcard patterns**: Avoid `.*` in `repository_pattern` for GHCR
4. **Check the logs**: Look for warnings about repository configuration

### Rate Limiting
- Implement exponential backoff in client code
- Use authenticated requests to get higher rate limits
- Consider caching responses to reduce API calls

### Network Connectivity
- Ensure network access to the registry API endpoints
- Check firewall rules and proxy configurations
- Verify SSL/TLS certificate validation settings
