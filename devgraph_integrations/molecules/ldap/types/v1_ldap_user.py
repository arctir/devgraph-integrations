from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1LdapUserEntitySpec(EntitySpec):
    """Specification for LDAP user entities."""

    dn: str
    uid: str | None = None
    cn: str | None = None  # Common Name
    sn: str | None = None  # Surname
    given_name: str | None = None
    display_name: str | None = None
    mail: str | None = None
    employee_id: str | None = None
    employee_type: str | None = None
    department: str | None = None
    title: str | None = None
    manager: str | None = None  # Manager DN
    telephone_number: str | None = None
    mobile: str | None = None
    office: str | None = None
    postal_address: str | None = None
    member_of: list[str] = []  # Group DNs this user is a member of
    create_timestamp: str | None = None
    modify_timestamp: str | None = None
    account_enabled: bool = True


class V1LdapUserEntityDefinition(EntityDefinition[V1LdapUserEntitySpec]):
    """Entity definition for LDAP users."""

    group: str = "entities.devgraph.ai"
    kind: str = "LdapUser"
    list_kind: str = "LdapUserList"
    plural: str = "ldapusers"
    singular: str = "ldapuser"
    name: str = "v1"
    spec_class: type = V1LdapUserEntitySpec
    description: str = (
        "An LDAP user representing a person from an LDAP directory service"
    )


class V1LdapUserEntity(Entity):
    """LDAP user entity."""

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "LdapUser"
    spec: V1LdapUserEntitySpec  # type: ignore[assignment]

    @property
    def plural(self) -> str:
        """Return the plural form of the kind."""
        return "ldapusers"
