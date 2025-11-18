from typing import Annotated

from pydantic import constr

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1ArgoApplicationEntitySpec(EntitySpec):
    name: Annotated[str, constr(min_length=1)]
    # description: Optional[str] = None
    # labels: Optional[List[str]] = None


class V1ArgoApplicationEntityDefinition(EntityDefinition[V1ArgoApplicationEntitySpec]):
    group: str = "entities.devgraph.ai"
    kind: str = "ArgoApplication"
    list_kind: str = "ArgoApplicationList"
    plural: str = "argoapplications"
    singular: str = "argoapplication"
    name: str = "v1"
    spec_class: type = V1ArgoApplicationEntitySpec
    display_name: str = "Argo Application"
    characteristics: list = ["deployment", "kubernetes", "gitops"]
    description: str = "Argo CD application deployed and managed by ArgoCD"


class V1ArgoApplicationEntity(Entity):
    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "ArgoApplication"
    spec: V1ArgoApplicationEntitySpec  # type: ignore[assignment]

    @property
    def plural(self) -> str:
        """Return the plural form of the kind."""
        return "argoapplications"

    @property
    def full_name(self) -> str:
        """Return the full name of the app in the format 'organization/name'."""
        return f"{self.spec.organization}/{self.spec.name}"
