from typing import Annotated

from pydantic import constr

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1GitlabHostingServiceEntitySpec(EntitySpec):
    api_url: Annotated[str, constr(min_length=1)] = "https://gitlab.com/api/v4"


class V1GitlabHostingServiceEntityDefinition(
    EntityDefinition[V1GitlabHostingServiceEntitySpec]
):
    group: str = "entities.devgraph.ai"
    kind: str = "GitlabHostingService"
    list_kind: str = "GitlabHostingServiceList"
    plural: str = "gitlabhostingservices"
    singular: str = "gitlabhostingservice"
    name: str = "v1"
    spec_class: type = V1GitlabHostingServiceEntitySpec
    description: str = "A GitLab hosting service that provides Git repository hosting and CI/CD features"


class V1GitlabHostingServiceEntity(Entity):
    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "GitlabHostingService"
    spec: V1GitlabHostingServiceEntitySpec  # type: ignore[assignment]

    @property
    def plural(self) -> str:
        """Return the plural form of the kind."""
        return "gitlabhostingservices"
