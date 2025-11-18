"""Project meta entity type.

This module defines the Project meta entity type, which serves as a base
type for any project or initiative that brings together multiple components,
teams, and resources to achieve specific goals.

The Project type provides common fields for tracking project metadata,
lifecycle, stakeholders, and relationships to other entities.
"""

from typing import Optional
from enum import Enum

from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class ProjectType(str, Enum):
    """Types of projects."""

    PRODUCT = "product"
    FEATURE = "feature"
    INITIATIVE = "initiative"
    RESEARCH = "research"
    INFRASTRUCTURE = "infrastructure"
    PLATFORM = "platform"
    TOOL = "tool"
    INTEGRATION = "integration"
    MIGRATION = "migration"
    OTHER = "other"


class ProjectStatus(str, Enum):
    """Status of projects."""

    PLANNED = "planned"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"
    NONE = "none"


class ProjectPriority(str, Enum):
    """Priority levels for projects."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    NONE = "none"


class V1ProjectEntitySpec(EntitySpec):
    """Specification for project entities.

    Defines common fields for any project that can be tracked
    in the Devgraph system.

    Attributes:
        project_type: The type of project
        name: Human-readable name of the project
        description: Project description
        status: Current project status
        priority: Project priority level
    """

    # Core identification
    project_type: ProjectType = ProjectType.OTHER
    name: str
    description: Optional[str] = None

    # Status and lifecycle
    status: ProjectStatus = ProjectStatus.NONE
    priority: Optional[ProjectPriority] = ProjectPriority.NONE


class V1ProjectEntityDefinition(EntityDefinition[V1ProjectEntitySpec]):
    """Entity definition for workstreams."""

    group: str = "entities.devgraph.ai"
    kind: str = "Workstream"
    list_kind: str = "WorkstreamList"
    plural: str = "workstreams"
    singular: str = "workstream"
    name: str = "v1"
    spec_class: type = V1ProjectEntitySpec
    display_name: str = "Workstream"
    characteristics: list = ["initiative", "organizational"]
    description: str = (
        "Workstreams and initiatives that organize work, resources, and deliverables"
    )


class V1ProjectEntity(Entity):
    """Workstream entity."""

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "Workstream"
    spec: V1ProjectEntitySpec  # type: ignore[assignment]

    @property
    def is_active(self) -> bool:
        """Check if project is in an active status."""
        return self.spec.status == ProjectStatus.ACTIVE

    @property
    def is_completed(self) -> bool:
        """Check if project is completed."""
        return self.spec.status == ProjectStatus.COMPLETED

    @property
    def status_summary(self) -> str:
        """Return a summary of project status."""
        return self.spec.status.value

    @property
    def full_identifier(self) -> str:
        """Return full project identifier."""
        return f"project:{self.metadata.name}"
