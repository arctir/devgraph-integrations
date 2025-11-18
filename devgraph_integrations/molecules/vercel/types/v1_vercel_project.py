from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1VercelProjectEntitySpec(EntitySpec):
    """Specification for Vercel project entities."""

    name: str
    id: str
    framework: str | None = None
    url: str | None = None
    description: str | None = None
    team_id: str | None = None
    created_at: int | str | None = None
    updated_at: int | str | None = None


class V1VercelProjectEntityDefinition(EntityDefinition[V1VercelProjectEntitySpec]):
    """Entity definition for Vercel projects."""

    group: str = "entities.devgraph.ai"
    kind: str = "VercelProject"
    list_kind: str = "VercelProjectList"
    plural: str = "vercelprojects"
    singular: str = "vercelproject"
    name: str = "v1"
    spec_class: type = V1VercelProjectEntitySpec
    display_name: str = "Vercel Project"
    characteristics: list = ["deployment", "web application", "hosting"]
    description: str = (
        "A Vercel project that manages deployments of web applications and sites"
    )


class V1VercelProjectEntity(Entity):
    """Vercel project entity."""

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "VercelProject"
    spec: V1VercelProjectEntitySpec  # type: ignore[assignment]

    @property
    def plural(self) -> str:
        """Return the plural form of the kind."""
        return "vercelprojects"
