"""FOSSA project entity definitions.

This module defines the entity types for representing FOSSA projects
in the Devgraph system, including specifications, definitions, and entity classes.
"""

from typing import Annotated, Optional

from pydantic import constr

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1FOSSAProjectEntitySpec(EntitySpec):
    """A FOSSA project specifies the details of a project managed by FOSSA.
    FOSSA provides details about a source code repository, including its license,
    dependencies, and compliance information.

    Attributes:
        project_id: FOSSA project ID (required)
        title: Project title/name (required)
        locator: FOSSA project locator string (optional)
        default_branch: Default branch name (optional)
        url: Repository URL from FOSSA (optional)
    """

    project_id: Annotated[str, constr(min_length=1)]
    title: Annotated[str, constr(min_length=1)]
    locator: Optional[str] = None
    default_branch: Optional[str] = None
    url: Optional[str] = None


class V1FOSSAProjectEntityDefinition(EntityDefinition[V1FOSSAProjectEntitySpec]):
    """Entity definition for FOSSA projects.

    Defines metadata about the FOSSA project entity type including
    API version, kind, and pluralization rules.
    """

    group: str = "entities.devgraph.ai"
    kind: str = "FOSSAProject"
    list_kind: str = "FOSSAProjectList"
    plural: str = "fossaprojects"
    singular: str = "fossaproject"
    name: str = "v1"
    spec_class: type = V1FOSSAProjectEntitySpec
    display_name: str = "FOSSA Project"
    characteristics: list = [
        "sbom",
        "dependencies",
        "license",
        "security",
        "compliance",
    ]
    description: str = (
        "A FOSSA project containing SBOM, license, dependency, and security compliance data"
    )


class V1FOSSAProjectEntity(Entity):
    """FOSSA project entity implementation.

    Represents a FOSSA project as a Devgraph entity with methods
    for accessing project properties and metadata.
    """

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "FOSSAProject"
    spec: V1FOSSAProjectEntitySpec  # type: ignore[assignment]

    @property
    def plural(self) -> str:
        """Return the plural form of the entity kind.

        Returns:
            The plural form 'fossaprojects'
        """
        return "fossaprojects"
