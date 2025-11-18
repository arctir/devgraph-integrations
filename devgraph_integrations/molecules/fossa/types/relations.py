"""FOSSA relation definitions."""
from devgraph_integrations.types.entities import EntityRelation


class FOSSAProjectScansRelation(EntityRelation):
    """Relation indicating a FOSSA project scans a repository/project."""

    relation: str = "SCANS"
