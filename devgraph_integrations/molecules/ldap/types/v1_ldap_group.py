from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1LdapGroupEntitySpec(EntitySpec):
    """Specification for LDAP group entities."""

    dn: str
    cn: str  # Common Name
    gid_number: int | str | None = None
    description: str | None = None
    group_type: str | None = None  # security, distribution, etc.
    members: list[str] = []  # Member DNs
    member_uids: list[str] = []  # Member UIDs for POSIX groups
    owner: str | None = None  # Owner DN
    managed_by: str | None = None  # Managed by DN
    mail: str | None = None  # Group email
    create_timestamp: str | None = None
    modify_timestamp: str | None = None


class V1LdapGroupEntityDefinition(EntityDefinition[V1LdapGroupEntitySpec]):
    """Entity definition for LDAP groups."""

    group: str = "entities.devgraph.ai"
    kind: str = "LdapGroup"
    list_kind: str = "LdapGroupList"
    plural: str = "ldapgroups"
    singular: str = "ldapgroup"
    name: str = "v1"
    spec_class: type = V1LdapGroupEntitySpec
    description: str = "An LDAP group representing a collection of users from an LDAP directory service"


class V1LdapGroupEntity(Entity):
    """LDAP group entity."""

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "LdapGroup"
    spec: V1LdapGroupEntitySpec  # type: ignore[assignment]

    @property
    def plural(self) -> str:
        """Return the plural form of the kind."""
        return "ldapgroups"
