from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1VercelDeploymentEntitySpec(EntitySpec):
    """Specification for Vercel deployment entities."""

    uid: str
    name: str
    url: str
    project_id: str
    state: str  # BUILDING, READY, ERROR, CANCELED
    type: str  # LAMBDA
    target: str | None = None  # production, preview
    created_at: int | str | None = None
    ready: int | str | None = None
    git_source: dict | None = None


class V1VercelDeploymentEntityDefinition(
    EntityDefinition[V1VercelDeploymentEntitySpec]
):
    """Entity definition for Vercel deployments."""

    group: str = "entities.devgraph.ai"
    kind: str = "VercelDeployment"
    list_kind: str = "VercelDeploymentList"
    plural: str = "verceldeployments"
    singular: str = "verceldeployment"
    name: str = "v1"
    spec_class: type = V1VercelDeploymentEntitySpec
    description: str = (
        "A Vercel deployment representing a specific version of a web application or site"
    )


class V1VercelDeploymentEntity(Entity):
    """Vercel deployment entity."""

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "VercelDeployment"
    spec: V1VercelDeploymentEntitySpec  # type: ignore[assignment]

    @property
    def plural(self) -> str:
        """Return the plural form of the kind."""
        return "verceldeployments"
