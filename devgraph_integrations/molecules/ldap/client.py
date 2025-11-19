"""LDAP client for directory operations.

This module provides a client for connecting to and querying LDAP directories,
including support for pagination, different authentication methods, and
various search scopes.
"""

from typing import Any, Dict, List, Optional

from ldap3 import ALL, BASE, LEVEL, SUBTREE, Connection, Server
from loguru import logger

from .config import LdapSelectorConfig


class LdapClient:
    """LDAP client for connecting to and querying LDAP directories.

    Provides methods to connect to LDAP servers and search for users,
    groups, and organizational units. Supports various authentication
    methods, encryption options, and paginated searches.

    Attributes:
        server: LDAP server hostname or IP
        port: LDAP server port
        use_tls: Whether to use STARTTLS
        use_ssl: Whether to use SSL/TLS
        bind_dn: Distinguished name for authentication
        bind_password: Password for authentication
        timeout: Connection timeout in seconds
        page_size: Page size for paginated searches
        connection: Active LDAP connection object
    """

    def __init__(
        self,
        server: str,
        port: int = 389,
        use_tls: bool = False,
        use_ssl: bool = False,
        bind_dn: Optional[str] = None,
        bind_password: Optional[str] = None,
        timeout: int = 30,
        page_size: int = 1000,
    ) -> None:
        """Initialize LDAP client.

        Args:
            server: LDAP server hostname or IP address
            port: LDAP server port (389 for plain, 636 for SSL)
            use_tls: Whether to use STARTTLS encryption
            use_ssl: Whether to use SSL/TLS connection
            bind_dn: Distinguished name for authentication (None for anonymous)
            bind_password: Password for authentication
            timeout: Connection timeout in seconds
            page_size: Page size for paginated searches
        """
        self.server = server
        self.port = port
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.timeout = timeout
        self.page_size = page_size
        self.connection = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to LDAP server.

        Raises:
            Exception: If connection to LDAP server fails
        """
        try:
            # Create server object
            server = Server(
                self.server,
                port=self.port,
                use_ssl=self.use_ssl,
                get_info=ALL,
                connect_timeout=self.timeout,
            )

            # Create connection
            self.connection = Connection(
                server,
                user=self.bind_dn,
                password=self.bind_password,
                auto_bind=True,
                auto_referrals=False,
            )

            # Start TLS if requested
            if self.use_tls and not self.use_ssl:
                self.connection.start_tls()

            logger.info(
                f"Successfully connected to LDAP server {self.server}:{self.port}"
            )

        except Exception as e:
            logger.error(
                f"Failed to connect to LDAP server {self.server}:{self.port}: {e}"
            )
            raise

    def _get_search_scope(self, scope_str: str) -> int:
        """Convert string scope to ldap3 scope constant.

        Args:
            scope_str: Scope string (BASE, ONELEVEL, or SUBTREE)

        Returns:
            Corresponding ldap3 scope constant, defaults to SUBTREE
        """
        scope_map = {
            "BASE": BASE,
            "ONELEVEL": LEVEL,
            "SUBTREE": SUBTREE,
        }
        return scope_map.get(scope_str.upper(), SUBTREE)

    def search(self, selector: LdapSelectorConfig) -> List[Dict[str, Any]]:
        """Search LDAP directory based on selector configuration.

        Performs paginated search to handle large result sets efficiently.

        Args:
            selector: Search configuration including base DN, filter, and scope

        Returns:
            List of entry dictionaries with DN and attributes, empty on failure
        """
        if not self.connection:
            logger.error("No LDAP connection available")
            return []

        try:
            scope = self._get_search_scope(selector.search_scope)

            # Perform paged search for large result sets
            entries = []
            cookie = None

            while True:
                success = self.connection.search(
                    search_base=selector.base_dn,
                    search_filter=selector.search_filter,
                    search_scope=scope,
                    attributes=selector.attributes,
                    paged_size=self.page_size,
                    paged_cookie=cookie,
                )

                if not success:
                    logger.error(f"LDAP search failed: {self.connection.result}")
                    break

                # Process entries
                for entry in self.connection.entries:
                    entry_dict = {"dn": entry.entry_dn, "attributes": {}}

                    # Convert attributes to dict
                    for attr_name in entry.entry_attributes:
                        attr_value = entry[attr_name].value
                        # Handle multi-valued attributes
                        if isinstance(attr_value, list) and len(attr_value) == 1:
                            attr_value = attr_value[0]
                        entry_dict["attributes"][attr_name] = attr_value

                    entries.append(entry_dict)

                # Check if there are more results
                cookie = (
                    self.connection.result.get("controls", {})
                    .get("1.2.840.113556.1.4.319", {})
                    .get("value", {})
                    .get("cookie")
                )
                if not cookie:
                    break

            logger.info(f"Found {len(entries)} entries for base DN: {selector.base_dn}")
            return entries

        except Exception as e:
            logger.error(f"Error searching LDAP directory: {e}")
            return []

    def get_users(self, selectors: List[LdapSelectorConfig]) -> List[Dict[str, Any]]:
        """Get user entries from LDAP using multiple selectors.

        Args:
            selectors: List of search configurations for finding users

        Returns:
            Combined list of all user entries found
        """
        all_users = []
        for selector in selectors:
            users = self.search(selector)
            all_users.extend(users)
        return all_users

    def get_groups(self, selectors: List[LdapSelectorConfig]) -> List[Dict[str, Any]]:
        """Get group entries from LDAP using multiple selectors.

        Args:
            selectors: List of search configurations for finding groups

        Returns:
            Combined list of all group entries found
        """
        all_groups = []
        for selector in selectors:
            groups = self.search(selector)
            all_groups.extend(groups)
        return all_groups

    def get_organizational_units(
        self, selectors: List[LdapSelectorConfig]
    ) -> List[Dict[str, Any]]:
        """Get organizational unit entries from LDAP using multiple selectors.

        Args:
            selectors: List of search configurations for finding organizational units

        Returns:
            Combined list of all organizational unit entries found
        """
        all_org_units = []
        for selector in selectors:
            org_units = self.search(selector)
            all_org_units.extend(org_units)
        return all_org_units

    def close(self) -> None:
        """Close LDAP connection and clean up resources."""
        if self.connection:
            self.connection.unbind()
            logger.info("LDAP connection closed")

    def __enter__(self) -> "LdapClient":
        """Context manager entry.

        Returns:
            Self for use in with statements
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - close connection.

        Args:
            exc_type: Exception type if any
            exc_val: Exception value if any
            exc_tb: Exception traceback if any
        """
        self.close()
