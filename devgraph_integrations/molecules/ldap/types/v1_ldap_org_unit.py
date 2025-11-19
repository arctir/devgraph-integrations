from devgraph_integrations.core.base import EntityDefinition
from devgraph_integrations.types.entities import Entity, EntitySpec


class V1LdapOrgUnitEntitySpec(EntitySpec):
    """Specification for LDAP organizational unit entities."""

    dn: str
    ou: str  # Organizational Unit name
    description: str | None = None
    postal_address: str | None = None
    postal_code: str | None = None
    street: str | None = None
    locality: str | None = None  # Locality/city (LDAP attribute: l)
    state: str | None = None  # State (LDAP attribute: st)
    country: str | None = None  # Country (LDAP attribute: c)
    telephone_number: str | None = None
    fax_number: str | None = None
    manager: str | None = None  # Manager DN
    business_category: str | None = None
    create_timestamp: str | None = None
    modify_timestamp: str | None = None


class V1LdapOrgUnitEntityDefinition(EntityDefinition[V1LdapOrgUnitEntitySpec]):
    """Entity definition for LDAP organizational units."""

    group: str = "entities.devgraph.ai"
    kind: str = "LdapOrgUnit"
    list_kind: str = "LdapOrgUnitList"
    plural: str = "ldaporgunits"
    singular: str = "ldaporgunit"
    name: str = "v1"
    spec_class: type = V1LdapOrgUnitEntitySpec
    description: str = (
        "An LDAP organizational unit representing a structural division within an LDAP directory"
    )


class V1LdapOrgUnitEntity(Entity):
    """LDAP organizational unit entity."""

    apiVersion: str = "entities.devgraph.ai/v1"
    kind: str = "LdapOrgUnit"
    spec: V1LdapOrgUnitEntitySpec  # type: ignore[assignment]

    @property
    def plural(self) -> str:
        """Return the plural form of the kind."""
        return "ldaporgunits"
