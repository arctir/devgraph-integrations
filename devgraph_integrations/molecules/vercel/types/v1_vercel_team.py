from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1VercelTeamEntitySpec(EntitySpec):
    """Specification for Vercel team entities."""

    id: str
    slug: str
    name: str
    avatar: str | None = None
    created_at: int | str | None = None


class V1VercelTeamEntityDefinition(EntityDefinition[V1VercelTeamEntitySpec]):
    """Entity definition for Vercel teams."""

    group: str = "entities.devgraph.ai"
    kind: str = "VercelTeam"
    list_kind: str = "VercelTeamList"
    plural: str = "vercelteams"
    singular: str = "vercelteam"
    name: str = "v1"
    spec_class: type = V1VercelTeamEntitySpec
    description: str = "A Vercel team that groups members and manages organizational access and permissions"


class V1VercelTeamEntity(Entity):
    """Vercel team entity."""

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "VercelTeam"
    spec: V1VercelTeamEntitySpec  # type: ignore[assignment]

    @property
    def plural(self) -> str:
        """Return the plural form of the kind."""
        return "vercelteams"
