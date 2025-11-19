from typing import Annotated

from pydantic import constr

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1GithubHostingServiceEntitySpec(EntitySpec):
    api_url: Annotated[str, constr(min_length=1)] = "https://api.github.com"


class V1GithubHostingServiceEntityDefinition(
    EntityDefinition[V1GithubHostingServiceEntitySpec]
):
    group: str = "entities.devgraph.ai"
    kind: str = "GithubHostingService"
    list_kind: str = "GithubHostingServiceList"
    plural: str = "githubhostingservices"
    singular: str = "githubhostingservice"
    name: str = "v1"
    spec_class: type = V1GithubHostingServiceEntitySpec
    description: str = (
        "A GitHub hosting service that provides Git repository hosting and collaboration features"
    )


class V1GithubHostingServiceEntity(Entity):
    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "GithubHostingService"
    spec: V1GithubHostingServiceEntitySpec  # type: ignore[assignment]

    @property
    def plural(self) -> str:
        """Return the plural form of the kind."""
        return "githubhostingservices"
