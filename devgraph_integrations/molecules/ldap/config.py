"""Configuration models for LDAP provider.

This module defines the configuration classes used to configure the LDAP
provider, including connection settings and object selection criteria.
"""
from pydantic import BaseModel

from devgraph_integrations.config.base import SensitiveBaseModel
from devgraph_integrations.molecules.base.config import MoleculeProviderConfig


class LdapSelectorConfig(BaseModel):
    """Configuration for selecting LDAP objects to discover.

    Defines search criteria for discovering specific types of LDAP objects
    within the directory tree.

    Attributes:
        base_dn: Base distinguished name to start search from
        search_filter: LDAP search filter (defaults to all objects)
        search_scope: Search scope (BASE, ONELEVEL, or SUBTREE)
        attributes: List of attributes to retrieve ("*" for all)
    """

    base_dn: str
    search_filter: str = "(objectClass=*)"
    search_scope: str = "SUBTREE"  # BASE, ONELEVEL, SUBTREE
    attributes: list[str] = ["*"]  # Attributes to retrieve, ["*"] for all


class LdapProviderConfig(MoleculeProviderConfig, SensitiveBaseModel):
    """Main configuration for LDAP provider.

    Contains all settings needed to connect to LDAP directory and configure
    object discovery behavior for users, groups, and organizational units.

    Attributes:
        server: LDAP server hostname or IP address
        port: LDAP server port (default 389 for plain, 636 for SSL)
        use_tls: Whether to use STARTTLS encryption
        use_ssl: Whether to use SSL/TLS connection
        bind_dn: Distinguished name for authentication (None for anonymous)
        bind_password: Password for authentication
        timeout: Connection timeout in seconds
        page_size: Page size for paginated searches
        user_selectors: List of selectors for discovering user objects
        group_selectors: List of selectors for discovering group objects
        org_unit_selectors: List of selectors for discovering OU objects

    Note:
        namespace field is inherited from MoleculeProviderConfig base class
    """

    server: str
    port: int = 389
    use_tls: bool = False
    use_ssl: bool = False
    bind_dn: str | None = None
    bind_password: str | None = None
    timeout: int = 30
    page_size: int = 1000

    # Discovery selectors for different LDAP object types
    user_selectors: list[LdapSelectorConfig] = []
    group_selectors: list[LdapSelectorConfig] = []
    org_unit_selectors: list[LdapSelectorConfig] = []
