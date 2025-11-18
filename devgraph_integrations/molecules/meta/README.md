# Meta Entity Types

This module provides meta entity types that serve as foundational abstractions for the Devgraph system. These types can be used as base classes, reference types, or templates for more specific provider entities.

## Available Meta Types

### 1. SoftwareComponent (`meta.devgraph.ai/v1`)

Represents any software artifact including repositories, packages, libraries, services, and applications.

**Key Fields:**
- `component_type`: Repository, package, service, application, etc.
- `name`: Human-readable component name
- `version`: Version string
- `repository_url`, `homepage_url`, `documentation_url`
- `languages`: Programming languages used
- `maintainers`: References to Person entities
- `dependencies`: References to other SoftwareComponent entities
- `lifecycle_stage`: Development, production, deprecated, etc.
- `health_status`: Overall health assessment

**Use Cases:**
- Track GitHub repositories across organizations
- Catalog npm packages and Docker images
- Map service dependencies
- Track software lifecycle and health

### 2. DeploymentComponent (`meta.devgraph.ai/v1`)

Represents running instances of software components in various environments and platforms.

**Key Fields:**
- `deployment_type`: Container, Kubernetes pod/deployment, cloud function, etc.
- `namespace`, `environment`, `platform`
- `image`, `version`, `replicas`, `status`
- `resource_requests`, `resource_limits`
- `software_component`: Reference to the underlying SoftwareComponent
- `dependencies`: Runtime dependencies on other deployments
- `monitoring_urls`, `log_urls`

**Use Cases:**
- Track Kubernetes deployments and pods
- Monitor container instances
- Map deployment dependencies
- Track resource utilization

### 3. Infrastructure (`meta.devgraph.ai/v1`)

Represents physical and virtual infrastructure resources that support software deployments.

**Key Fields:**
- `infrastructure_type`: Server, VM, cluster, database, load balancer, etc.
- `environment`, `region`, `provider`
- `capacity`, `utilization`: Resource metrics
- `endpoints`: Network endpoints
- `owner`: Reference to Team or Person entity
- `supports`: References to DeploymentComponent entities

**Use Cases:**
- Track cloud resources (AWS EC2, GCP VMs)
- Monitor Kubernetes clusters and nodes
- Catalog databases and storage systems
- Map infrastructure dependencies

### 4. Person (`meta.devgraph.ai/v1`)

Represents individual people including developers, operators, and other stakeholders.

**Key Fields:**
- `display_name`, `email`, `username`
- `roles`: Developer, DevOps, architect, manager, etc.
- `title`, `department`, `location`
- `manager`: Reference to manager Person entity
- `teams`: References to Team entities
- `skills`: Technical skills and capabilities
- `github_username`, `slack_user_id`

**Use Cases:**
- Sync from LDAP/Active Directory
- Track code ownership and expertise
- Map organizational structure
- Connect people to their work

### 5. Team (`meta.devgraph.ai/v1`)

Represents teams, groups, and organizational units.

**Key Fields:**
- `display_name`, `team_type`, `description`
- `members`: References to Person entities
- `leads`: References to team lead Person entities
- `owned_software`: References to SoftwareComponent entities
- `owned_infrastructure`: References to Infrastructure entities
- `responsibilities`: Areas of responsibility
- `oncall_rotation`: On-call information

**Use Cases:**
- Model organizational structure
- Track ownership and responsibility
- Map teams to their services and infrastructure
- Support incident response workflows

### 6. SecurityComponent (`meta.devgraph.ai/v1`)

Represents security-related entities including vulnerabilities, policies, and certificates.

**Key Fields:**
- `component_type`: Vulnerability, certificate, secret, policy, etc.
- `severity`: Critical, high, medium, low
- `status`: Active, resolved, acknowledged
- `cve_id`, `cvss_score`: Vulnerability details
- `affected_components`: References to affected entities
- `assignee`: Reference to Person responsible
- `expiry_date`: For certificates and time-sensitive items

**Use Cases:**
- Track security vulnerabilities
- Monitor certificate expiration
- Manage security policies
- Connect security issues to affected components

## Usage Examples

### Creating Meta Entity Instances

```python
from devgraph_discovery.types.meta import (
    V1SoftwareComponentEntity,
    V1SoftwareComponentEntitySpec,
    SoftwareComponentType
)
from devgraph_discovery.types.entities import EntityMetadata

# Create a software component
component = V1SoftwareComponentEntity(
    metadata=EntityMetadata(
        name="my-api-service",
        namespace="production",
        labels={"team": "backend", "criticality": "high"}
    ),
    spec=V1SoftwareComponentEntitySpec(
        component_type=SoftwareComponentType.SERVICE,
        name="My API Service",
        version="v1.2.3",
        repository_url="https://github.com/company/my-api",
        languages=["Python", "JavaScript"],
        lifecycle_stage="production",
        health_status="healthy"
    )
)
```

### Extending Meta Types in Providers

```python
# GitHub provider can reference SoftwareComponent
from devgraph_discovery.types.meta import V1SoftwareComponentEntity

class V1GithubRepositoryEntity(V1SoftwareComponentEntity):
    # Inherits all SoftwareComponent fields
    # Add GitHub-specific extensions
    pass
```

### Cross-Provider Relationships

```python
# Link a GitHub repository to its Kubernetes deployment
github_repo_spec.spec.deployment_references = ["k8s:default/my-api-deployment"]
k8s_deployment_spec.spec.software_component = "github:company/my-api"
```

## Provider Integration

The `MetaProvider` exposes these entity definitions to the Devgraph system, making them available for:

1. **Reference by other providers**: GitHub repositories can reference SoftwareComponent type
2. **Cross-provider relationships**: Link entities across different systems
3. **Query and visualization**: Use meta types for unified views
4. **Policy enforcement**: Apply policies based on meta type classifications

## Configuration

Add to your discovery configuration:

```yaml
providers:
  - name: meta
    type: meta
    every: 86400  # Run once per day to register definitions
```

The meta provider will register all meta entity definitions, making them available for use by other providers and for direct entity creation.