from devgraph_integrations.types.entities import EntityRelation, FieldSelectedEntityRelation


class VercelProjectBelongsToTeamRelation(EntityRelation):
    """Relation: Vercel Project belongs to Team"""

    relation: str = "BELONGS_TO"


class VercelDeploymentBelongsToProjectRelation(EntityRelation):
    """Relation: Vercel Deployment belongs to Project"""

    relation: str = "BELONGS_TO"


class VercelProjectUsesRepositoryRelation(FieldSelectedEntityRelation):
    """Relation: Vercel Project uses Repository (with field selector)"""

    relation: str = "USES"
