from devgraph_integrations.types.entities import EntityRelation


class LdapUserMemberOfGroupRelation(EntityRelation):
    """Relation: LDAP User is member of Group"""

    relation: str = "MEMBER_OF"


class LdapUserReportsToUserRelation(EntityRelation):
    """Relation: LDAP User reports to another User"""

    relation: str = "REPORTS_TO"


class LdapUserBelongsToOrgUnitRelation(EntityRelation):
    """Relation: LDAP User belongs to Organizational Unit"""

    relation: str = "BELONGS_TO"


class LdapGroupBelongsToOrgUnitRelation(EntityRelation):
    """Relation: LDAP Group belongs to Organizational Unit"""

    relation: str = "BELONGS_TO"


class LdapOrgUnitBelongsToOrgUnitRelation(EntityRelation):
    """Relation: LDAP Organizational Unit belongs to parent Organizational Unit"""

    relation: str = "BELONGS_TO"


class LdapGroupOwnedByUserRelation(EntityRelation):
    """Relation: LDAP Group is owned by User"""

    relation: str = "OWNED_BY"


class LdapGroupManagedByUserRelation(EntityRelation):
    """Relation: LDAP Group is managed by User"""

    relation: str = "MANAGED_BY"
