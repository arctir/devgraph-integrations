"""LDAP molecule for Devgraph discovery.

This module provides LDAP directory integration for Devgraph, enabling
discovery and synchronization of users, groups, and organizational units
from LDAP directories.

The module includes:
- LdapProvider: Main provider class for LDAP discovery
- LdapProviderConfig: Configuration model for LDAP connections
- LdapClient: Client for LDAP directory operations
- Entity types: V1LdapUserEntity, V1LdapGroupEntity, V1LdapOrgUnitEntity
"""

from .client import LdapClient
from .config import LdapProviderConfig, LdapSelectorConfig
from .provider import LdapProvider
from .types.v1_ldap_group import (
    V1LdapGroupEntity,
    V1LdapGroupEntityDefinition,
    V1LdapGroupEntitySpec,
)
from .types.v1_ldap_org_unit import (
    V1LdapOrgUnitEntity,
    V1LdapOrgUnitEntityDefinition,
    V1LdapOrgUnitEntitySpec,
)
from .types.v1_ldap_user import (
    V1LdapUserEntity,
    V1LdapUserEntityDefinition,
    V1LdapUserEntitySpec,
)

__version__ = "1.0.0"
__molecule_metadata__ = {
    "version": __version__,
    "name": "ldap",
    "display_name": "LDAP",
    "description": "Discover LDAP users, groups, and organizational units from directory services",
    "logo": {
        "reactIcons": "PiUsersThree"
    },  # react-icons identifier (from react-icons/pi - Phosphor Icons)
    "homepage_url": "https://ldap.com",
    "docs_url": "https://ldap.com/learn-about-ldap/",
    "capabilities": [
        "discovery",
    ],
    "entity_types": [
        "LdapUser",
        "LdapGroup",
        "LdapOrgUnit",
    ],
    "relation_types": [
        "LdapUserMemberOfGroup",
        "LdapGroupBelongsToOrgUnit",
    ],
    "requires_auth": False,  # Can use anonymous bind
    "auth_types": ["bind_dn", "anonymous"],
    "min_framework_version": "0.1.0",
}

__all__ = [
    # Provider classes
    "LdapProvider",
    "LdapProviderConfig",
    "LdapSelectorConfig",
    "LdapClient",
    # User entity types
    "V1LdapUserEntity",
    "V1LdapUserEntitySpec",
    "V1LdapUserEntityDefinition",
    # Group entity types
    "V1LdapGroupEntity",
    "V1LdapGroupEntitySpec",
    "V1LdapGroupEntityDefinition",
    # Organizational unit entity types
    "V1LdapOrgUnitEntity",
    "V1LdapOrgUnitEntitySpec",
    "V1LdapOrgUnitEntityDefinition",
    # Metadata
    "__version__",
    "__molecule_metadata__",
]
