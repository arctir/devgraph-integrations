from typing import Annotated

from pydantic import constr

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1ArgoProjectEntitySpec(EntitySpec):
    name: Annotated[str, constr(min_length=1)]
    # description: Optional[str] = None
    # labels: Optional[List[str]] = None


class V1ArgoProjectEntityDefinition(EntityDefinition[V1ArgoProjectEntitySpec]):
    group: str = "entities.devgraph.ai"
    kind: str = "ArgoProject"
    list_kind: str = "ArgoProjectList"
    plural: str = "argoprojects"
    singular: str = "argoproject"
    name: str = "v1"
    spec_class: type = V1ArgoProjectEntitySpec
    display_name: str = "Argo Project"
    characteristics: list = ["configuration", "kubernetes", "gitops"]
    description: str = "Argo CD project that groups and manages related applications"


class V1ArgoProjectEntity(Entity):
    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "ArgoProject"
    spec: V1ArgoProjectEntitySpec  # type: ignore[assignment]

    @property
    def plural(self) -> str:
        """Return the plural form of the kind."""
        return "argoprojects"

    @property
    def full_name(self) -> str:
        """Return the full name of the project in the format 'organization/name'."""
        return f"{self.spec.organization}/{self.spec.name}"
