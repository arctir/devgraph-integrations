from typing import Annotated

from pydantic import constr

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1ArgoInstanceEntitySpec(EntitySpec):
    api_url: Annotated[str, constr(min_length=1)]


class V1ArgoInstanceEntityDefinition(EntityDefinition[V1ArgoInstanceEntitySpec]):
    group: str = "entities.devgraph.ai"
    kind: str = "ArgoInstance"
    list_kind: str = "ArgoInstanceList"
    plural: str = "argoinstances"
    singular: str = "argoinstance"
    name: str = "v1"
    spec_class: type = V1ArgoInstanceEntitySpec
    display_name: str = "Argo Instance"
    characteristics: list = ["infrastructure", "kubernetes", "gitops"]
    description: str = "An Argo CD instance that manages application deployments"


class V1ArgoInstanceEntity(Entity):
    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "ArgoInstance"
    spec: V1ArgoInstanceEntitySpec  # type: ignore[assignment]

    @property
    def plural(self) -> str:
        """Return the plural form of the kind."""
        return "argoinstances"
