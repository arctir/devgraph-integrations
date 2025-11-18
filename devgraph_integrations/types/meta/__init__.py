"""Meta entity types for Devgraph.

This module provides abstract and base entity types that can be used across
different providers to establish common patterns and relationships.

Meta entity types include:
- People: Base for human entities (users, teams, organizations)
- Workstream: Base for workstreams and initiatives
"""

from .v1_people import (
    V1PersonEntity,
    V1PersonEntityDefinition,
    V1PersonEntitySpec,
    V1TeamEntity,
    V1TeamEntityDefinition,
    V1TeamEntitySpec,
)

from .v1_project import (
    V1ProjectEntity,
    V1ProjectEntityDefinition,
    V1ProjectEntitySpec,
)

__all__ = [
    # People
    "V1PersonEntity",
    "V1PersonEntityDefinition",
    "V1PersonEntitySpec",
    "V1TeamEntity",
    "V1TeamEntityDefinition",
    "V1TeamEntitySpec",
    # Workstream (formerly Project)
    "V1ProjectEntity",
    "V1ProjectEntityDefinition",
    "V1ProjectEntitySpec",
]
