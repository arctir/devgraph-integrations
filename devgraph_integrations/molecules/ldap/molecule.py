"""LDAP molecule facade."""

from typing import Any, Dict, Optional, Type

from devgraph_integrations.core.molecule import Molecule


class LdapMolecule(Molecule):
    """LDAP molecule providing discovery capabilities."""

    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "name": "ldap",
            "display_name": "LDAP",
            "description": "Discover LDAP users, groups, and organizational units from directory services",
            "logo": {"reactIcons": "PiUsersThree"},
            "homepage_url": "https://ldap.com",
            "docs_url": "https://ldap.com/learn-about-ldap/",
            "capabilities": ["discovery"],
            "entity_types": ["LdapUser", "LdapGroup", "LdapOrgUnit"],
            "relation_types": ["LdapUserMemberOfGroup", "LdapGroupBelongsToOrgUnit"],
            "requires_auth": False,  # Can use anonymous bind
            "auth_types": ["bind_dn", "anonymous"],
            "min_framework_version": "0.1.0",
        }

    @staticmethod
    def get_discovery_provider() -> Optional[Type[Any]]:
        from .provider import LdapProvider

        return LdapProvider
