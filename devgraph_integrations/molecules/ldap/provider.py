"""LDAP provider for discovering users, groups, and organizational units.

This module provides an LDAP provider that discovers and synchronizes
LDAP directory objects into the Devgraph entity system.
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from devgraph_integrations.molecules.base.reconciliation import (
    FullStateReconciliation,
    ReconcilingMoleculeProvider,
)
from devgraph_integrations.types.entities import Entity

from .client import LdapClient
from .config import LdapProviderConfig
from .types.v1_ldap_group import V1LdapGroupEntity, V1LdapGroupEntitySpec
from .types.v1_ldap_org_unit import V1LdapOrgUnitEntity, V1LdapOrgUnitEntitySpec
from .types.v1_ldap_user import V1LdapUserEntity, V1LdapUserEntitySpec


class LdapProvider(ReconcilingMoleculeProvider):
    """LDAP provider for discovering directory objects.

    Connects to LDAP directories and discovers users, groups, and organizational
    units based on configured selectors. Transforms LDAP attributes into
    standardized entity specifications.

    Attributes:
        _config_cls: Configuration class for LDAP provider
        config: LDAP provider configuration
        client: LDAP client for directory operations
    """

    _config_cls = LdapProviderConfig

    def __init__(self, name: str, every: int, config: LdapProviderConfig) -> None:
        """Initialize LDAP provider.

        Args:
            name: Unique name for this provider instance
            every: Interval in seconds for reconciliation runs
            config: LDAP provider configuration
        """
        # Create reconciliation strategy using DN as the unique key
        reconciliation_strategy = FullStateReconciliation()
        super().__init__(name, every, config, reconciliation_strategy)

    def _should_init_client(self) -> bool:
        """LDAP providers should initialize clients."""
        return True

    def _init_client(self, config: LdapProviderConfig) -> LdapClient:
        """Initialize LDAP client.

        Args:
            config: LDAP provider configuration

        Returns:
            Initialized LDAP client
        """
        return LdapClient(
            server=config.server,
            port=config.port,
            use_tls=config.use_tls,
            use_ssl=config.use_ssl,
            bind_dn=config.bind_dn,
            bind_password=config.bind_password,
            timeout=config.timeout,
            page_size=config.page_size,
        )

    def _discover_current_entities(self) -> List[Entity]:
        """Discover all entities that should currently exist in LDAP.

        Returns:
            List of entities representing the current state in LDAP
        """
        entities = []

        # Discover users
        if self.config.user_selectors:
            logger.debug("Discovering LDAP users")
            user_entries = self.client.get_users(self.config.user_selectors)
            user_entities = self._process_with_error_handling(
                user_entries, self._create_user_entity, "LDAP user"
            )
            entities.extend(user_entities)
            logger.debug(f"Discovered {len(user_entities)} LDAP user entities")

        # Discover groups
        if self.config.group_selectors:
            logger.debug("Discovering LDAP groups")
            group_entries = self.client.get_groups(self.config.group_selectors)
            group_entities = self._process_with_error_handling(
                group_entries, self._create_group_entity, "LDAP group"
            )
            entities.extend(group_entities)
            logger.debug(f"Discovered {len(group_entities)} LDAP group entities")

        # Discover organizational units
        if self.config.org_unit_selectors:
            logger.debug("Discovering LDAP organizational units")
            ou_entries = self.client.get_organizational_units(
                self.config.org_unit_selectors
            )
            ou_entities = self._process_with_error_handling(
                ou_entries, self._create_org_unit_entity, "LDAP organizational unit"
            )
            entities.extend(ou_entities)
            logger.debug(
                f"Discovered {len(ou_entities)} LDAP organizational unit entities"
            )

        return entities

    def _get_managed_entity_kinds(self) -> List[str]:
        """Get list of entity kinds managed by this LDAP provider.

        Returns:
            List of LDAP entity kind strings
        """
        return ["LdapUser", "LdapGroup", "LdapOrgUnit"]

    def _create_user_entity(
        self, user_entry: Dict[str, Any]
    ) -> Optional[V1LdapUserEntity]:
        """Create LDAP user entity from directory entry.

        Args:
            user_entry: LDAP user entry with DN and attributes

        Returns:
            Created user entity or None if creation failed
        """
        attrs = user_entry.get("attributes", {})
        dn = user_entry.get("dn", "")

        # Extract common name or uid for entity name
        entity_name = (
            self._get_entity_name_from_dn(dn) or attrs.get("uid") or attrs.get("cn")
        )
        if not entity_name:
            logger.warning(f"No suitable name found for user DN: {dn}")
            return None

        # Handle multi-valued attributes safely
        def get_attr_value(attr_name: str, is_list: bool = False) -> Any:
            value = attrs.get(attr_name)
            if value is None:
                return [] if is_list else None
            if is_list and not isinstance(value, list):
                return [value]
            if not is_list and isinstance(value, list) and len(value) == 1:
                return value[0]
            return value

        spec = V1LdapUserEntitySpec(
            dn=dn,
            uid=get_attr_value("uid"),
            cn=get_attr_value("cn"),
            sn=get_attr_value("sn"),
            given_name=get_attr_value("givenName"),
            display_name=get_attr_value("displayName"),
            mail=get_attr_value("mail"),
            employee_id=get_attr_value("employeeID"),
            employee_type=get_attr_value("employeeType"),
            department=get_attr_value("department"),
            title=get_attr_value("title"),
            manager=get_attr_value("manager"),
            telephone_number=get_attr_value("telephoneNumber"),
            mobile=get_attr_value("mobile"),
            office=get_attr_value("physicalDeliveryOfficeName"),
            postal_address=get_attr_value("postalAddress"),
            member_of=get_attr_value("memberOf", is_list=True),
            create_timestamp=get_attr_value("createTimestamp"),
            modify_timestamp=get_attr_value("modifyTimestamp"),
            account_enabled=not bool(attrs.get("userAccountControl") == "514"),
        )

        return self._create_entity(
            entity_class=V1LdapUserEntity,
            name=entity_name,
            spec=spec,
            labels={"ldap.server": self.config.server},
        )

    def _create_group_entity(
        self, group_entry: Dict[str, Any]
    ) -> Optional[V1LdapGroupEntity]:
        """Create LDAP group entity from directory entry.

        Args:
            group_entry: LDAP group entry with DN and attributes

        Returns:
            Created group entity or None if creation failed
        """
        attrs = group_entry.get("attributes", {})
        dn = group_entry.get("dn", "")

        # Extract common name for entity name
        entity_name = attrs.get("cn")
        if not entity_name:
            entity_name = self._get_entity_name_from_dn(dn)

        if not entity_name:
            logger.warning(f"No suitable name found for group DN: {dn}")
            return None

        # Handle multi-valued attributes safely
        def get_attr_value(attr_name: str, is_list: bool = False) -> Any:
            value = attrs.get(attr_name)
            if value is None:
                return [] if is_list else None
            if is_list and not isinstance(value, list):
                return [value]
            if not is_list and isinstance(value, list) and len(value) == 1:
                return value[0]
            return value

        # Handle gidNumber which could be string or int
        gid_number = get_attr_value("gidNumber")
        if gid_number and isinstance(gid_number, str):
            try:
                gid_number = int(gid_number)
            except ValueError:
                pass  # Keep as string if conversion fails

        spec = V1LdapGroupEntitySpec(
            dn=dn,
            cn=entity_name,
            gid_number=gid_number,
            description=get_attr_value("description"),
            group_type=get_attr_value("groupType"),
            members=get_attr_value("member", is_list=True),
            member_uids=get_attr_value("memberUid", is_list=True),
            owner=get_attr_value("owner"),
            managed_by=get_attr_value("managedBy"),
            mail=get_attr_value("mail"),
            create_timestamp=get_attr_value("createTimestamp"),
            modify_timestamp=get_attr_value("modifyTimestamp"),
        )

        return self._create_entity(
            entity_class=V1LdapGroupEntity,
            name=entity_name,
            spec=spec,
            labels={"ldap.server": self.config.server},
        )

    def _create_org_unit_entity(
        self, ou_entry: Dict[str, Any]
    ) -> Optional[V1LdapOrgUnitEntity]:
        """Create LDAP organizational unit entity from directory entry.

        Args:
            ou_entry: LDAP OU entry with DN and attributes

        Returns:
            Created organizational unit entity or None if creation failed
        """
        attrs = ou_entry.get("attributes", {})
        dn = ou_entry.get("dn", "")

        # Extract OU name for entity name
        entity_name = attrs.get("ou")
        if not entity_name:
            entity_name = self._get_entity_name_from_dn(dn)

        if not entity_name:
            logger.warning(f"No suitable name found for OU DN: {dn}")
            return None

        # Handle multi-valued attributes safely
        def get_attr_value(attr_name: str) -> Any:
            value = attrs.get(attr_name)
            if isinstance(value, list) and len(value) == 1:
                return value[0]
            return value

        spec = V1LdapOrgUnitEntitySpec(
            dn=dn,
            ou=entity_name,
            description=get_attr_value("description"),
            postal_address=get_attr_value("postalAddress"),
            postal_code=get_attr_value("postalCode"),
            street=get_attr_value("street"),
            l=get_attr_value("l"),
            st=get_attr_value("st"),
            c=get_attr_value("c"),
            telephone_number=get_attr_value("telephoneNumber"),
            fax_number=get_attr_value("facsimileTelephoneNumber"),
            manager=get_attr_value("manager"),
            business_category=get_attr_value("businessCategory"),
            create_timestamp=get_attr_value("createTimestamp"),
            modify_timestamp=get_attr_value("modifyTimestamp"),
        )

        return self._create_entity(
            entity_class=V1LdapOrgUnitEntity,
            name=entity_name,
            spec=spec,
            labels={"ldap.server": self.config.server},
        )

    def _get_entity_name_from_dn(self, dn: str) -> Optional[str]:
        """Extract entity name from DN.

        Args:
            dn: Distinguished name

        Returns:
            Extracted name or None if extraction failed
        """
        if not dn:
            return None

        try:
            # Extract the first component (usually CN=name or OU=name)
            first_component = dn.split(",")[0].strip()
            if "=" in first_component:
                return first_component.split("=", 1)[1].strip()
        except (IndexError, ValueError):
            pass

        return None

    def _create_relations_for_entities(self, entities: List[Entity]) -> List:
        """Create relations for LDAP entities.

        Args:
            entities: Entities to create relations for

        Returns:
            List of relation objects
        """
        from .types.relations import (
            LdapGroupBelongsToOrgUnitRelation,
            LdapGroupManagedByUserRelation,
            LdapGroupOwnedByUserRelation,
            LdapOrgUnitBelongsToOrgUnitRelation,
            LdapUserBelongsToOrgUnitRelation,
            LdapUserMemberOfGroupRelation,
            LdapUserReportsToUserRelation,
        )

        relations = []

        # Build lookup maps
        user_dn_to_entity = {}
        group_dn_to_entity = {}
        ou_dn_to_entity = {}

        for entity in entities:
            if entity.kind == "LdapUser":
                user_dn_to_entity[entity.spec.dn] = entity
            elif entity.kind == "LdapGroup":
                group_dn_to_entity[entity.spec.dn] = entity
            elif entity.kind == "LdapOrgUnit":
                ou_dn_to_entity[entity.spec.dn] = entity

        # Create user relations
        for user_entity in user_dn_to_entity.values():
            # User MEMBER_OF Group
            if hasattr(user_entity.spec, "member_of") and user_entity.spec.member_of:
                for group_dn in user_entity.spec.member_of:
                    if group_dn in group_dn_to_entity:
                        relation = self.create_relation_with_metadata(
                            LdapUserMemberOfGroupRelation,
                            source=user_entity.reference,
                            target=group_dn_to_entity[group_dn].reference,
                            namespace=self.config.namespace,
                        )
                        relations.append(relation)

            # User REPORTS_TO User
            if hasattr(user_entity.spec, "manager") and user_entity.spec.manager:
                manager_dn = user_entity.spec.manager
                if manager_dn in user_dn_to_entity:
                    relation = self.create_relation_with_metadata(
                        LdapUserReportsToUserRelation,
                        source=user_entity.reference,
                        target=user_dn_to_entity[manager_dn].reference,
                        namespace=self.config.namespace,
                    )
                    relations.append(relation)

            # User BELONGS_TO OrgUnit (based on DN hierarchy)
            user_parent_dn = self._get_parent_dn(user_entity.spec.dn)
            if user_parent_dn and user_parent_dn in ou_dn_to_entity:
                relation = self.create_relation_with_metadata(
                    LdapUserBelongsToOrgUnitRelation,
                    source=user_entity.reference,
                    target=ou_dn_to_entity[user_parent_dn].reference,
                    namespace=self.config.namespace,
                )
                relations.append(relation)

        # Create group relations
        for group_entity in group_dn_to_entity.values():
            # Group BELONGS_TO OrgUnit (based on DN hierarchy)
            group_parent_dn = self._get_parent_dn(group_entity.spec.dn)
            if group_parent_dn and group_parent_dn in ou_dn_to_entity:
                relation = self.create_relation_with_metadata(
                    LdapGroupBelongsToOrgUnitRelation,
                    source=group_entity.reference,
                    target=ou_dn_to_entity[group_parent_dn].reference,
                    namespace=self.config.namespace,
                )
                relations.append(relation)

            # Group OWNED_BY User
            if hasattr(group_entity.spec, "owner") and group_entity.spec.owner:
                owner_dn = group_entity.spec.owner
                if owner_dn in user_dn_to_entity:
                    relation = self.create_relation_with_metadata(
                        LdapGroupOwnedByUserRelation,
                        source=group_entity.reference,
                        target=user_dn_to_entity[owner_dn].reference,
                        namespace=self.config.namespace,
                    )
                    relations.append(relation)

            # Group MANAGED_BY User
            if (
                hasattr(group_entity.spec, "managed_by")
                and group_entity.spec.managed_by
            ):
                managed_by_dn = group_entity.spec.managed_by
                if managed_by_dn in user_dn_to_entity:
                    relation = self.create_relation_with_metadata(
                        LdapGroupManagedByUserRelation,
                        source=group_entity.reference,
                        target=user_dn_to_entity[managed_by_dn].reference,
                        namespace=self.config.namespace,
                    )
                    relations.append(relation)

        # Create org unit relations
        for ou_entity in ou_dn_to_entity.values():
            # OrgUnit BELONGS_TO parent OrgUnit (based on DN hierarchy)
            ou_parent_dn = self._get_parent_dn(ou_entity.spec.dn)
            if ou_parent_dn and ou_parent_dn in ou_dn_to_entity:
                relation = self.create_relation_with_metadata(
                    LdapOrgUnitBelongsToOrgUnitRelation,
                    source=ou_entity.reference,
                    target=ou_dn_to_entity[ou_parent_dn].reference,
                    namespace=self.config.namespace,
                )
                relations.append(relation)

        logger.info(f"Created {len(relations)} LDAP relations")
        return relations

    def _get_parent_dn(self, dn: str) -> Optional[str]:
        """Get parent DN from a DN string.

        Args:
            dn: Distinguished name

        Returns:
            Parent DN or None if no parent
        """
        if not dn or "," not in dn:
            return None

        try:
            # Remove the first component to get parent
            components = dn.split(",", 1)
            if len(components) > 1:
                return components[1].strip()
        except (IndexError, ValueError):
            pass

        return None

    def close(self) -> None:
        """Close provider and clean up resources."""
        if self.client:
            self.client.close()
        super().close()
