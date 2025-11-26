"""Base reconciliation patterns for molecule providers.

This module provides common reconciliation strategies to keep the graph
in sync with source systems, including proper deletion detection and
entity lifecycle management.
"""

import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Tuple

from devgraph_client.api.entities import get_entities
from devgraph_client.client import AuthenticatedClient
from loguru import logger

from devgraph_integrations.core.state import GraphMutations
from devgraph_integrations.types.entities import Entity, EntityReference

from .provider import MoleculeProvider


class ReconciliationStrategy(ABC):
    """Abstract base for reconciliation strategies."""

    @abstractmethod
    def reconcile(
        self,
        current_entities: List[Entity],
        existing_entities: List[Entity],
        provider_name: str,
    ) -> Tuple[List[Entity], List[Entity], List[EntityReference]]:
        """
        Reconcile current and existing entities.

        Args:
            current_entities: Entities that should exist according to source
            existing_entities: Entities that currently exist in graph
            provider_name: Name of the provider performing reconciliation

        Returns:
            Tuple of (entities_to_create, entities_to_update, entities_to_delete)
        """
        pass


class FullStateReconciliation(ReconciliationStrategy):
    """Full state reconciliation compares complete current vs existing state."""

    def __init__(self):
        """Initialize full state reconciliation strategy."""
        pass

    def get_entity_key(self, entity) -> str:
        """Get unique key for entity using its ID."""
        return entity.id

    def reconcile(
        self,
        current_entities: List[Entity],
        existing_entities: List[Entity],
        provider_name: str,
    ) -> Tuple[List[Entity], List[Entity], List[EntityReference]]:
        """Perform full state reconciliation."""

        # Build lookup maps by unique key
        current_by_key = {self.get_entity_key(e): e for e in current_entities}
        existing_by_key = {self.get_entity_key(e): e for e in existing_entities}

        creates, updates, deletes = [], [], []

        # Find creates and updates
        for key, current_entity in current_by_key.items():
            if key not in existing_by_key:
                # Entity doesn't exist in graph - create it
                current_entity.mark_updated(source=provider_name)
                # Store fingerprint on entity that will be created
                fingerprint = self._compute_fingerprint(current_entity)
                self._store_fingerprint(current_entity, fingerprint)
                creates.append(current_entity)
                if current_entity.kind == "GithubHostingService":
                    logger.warning(
                        f"CREATING GitHub hosting service: {current_entity.metadata.name} (key: {key})"
                    )
                logger.debug(f"Will create entity: {current_entity.id}")

            else:
                # Entity exists - check if it needs updating
                existing_entity = existing_by_key[key]
                if self._needs_update(current_entity, existing_entity):
                    current_entity.mark_updated(source=provider_name)
                    # Store fingerprint on entity that will be updated
                    fingerprint = self._compute_fingerprint(current_entity)
                    self._store_fingerprint(current_entity, fingerprint)
                    updates.append(current_entity)
                    if current_entity.kind == "GithubHostingService":
                        logger.warning(
                            f"UPDATING GitHub hosting service: {current_entity.metadata.name} (key: {key})"
                        )
                    logger.debug(f"Will update entity: {current_entity.id}")
                else:
                    # Entity unchanged but mark as seen (if status exists)
                    if hasattr(existing_entity, "status"):
                        existing_entity.status.last_seen = datetime.now(timezone.utc)
                        existing_entity.status.discovery_source = provider_name

        # Find deletions - entities in graph but not in current source
        for key, existing_entity in existing_by_key.items():
            if key not in current_by_key:
                # Only delete entities that belong to this provider
                # Check if entity has status and discovery_source
                if hasattr(existing_entity, "status") and hasattr(
                    existing_entity.status, "discovery_source"
                ):
                    if existing_entity.status.discovery_source == provider_name:
                        # Create reference - use property if available, otherwise create manually
                        # Use the full entity object for deletion, not just a reference
                        # GraphMutations.delete_entities expects List[Entity], not List[EntityReference]
                        deletes.append(existing_entity)

                        # Extra logging for Project entities to debug unexpected deletions
                        if existing_entity.kind == "Project":
                            logger.error(
                                f"UNEXPECTED: Provider '{provider_name}' is deleting Project entity: "
                                f"{existing_entity.kind}:{existing_entity.metadata.name} (ID: {existing_entity.id})"
                            )
                            logger.error(
                                f"Provider managed kinds: {self._get_managed_entity_kinds()}"
                            )

                        logger.warning(
                            f"DELETING entity not found in current source: {existing_entity.kind}:{existing_entity.metadata.name} (key: {key})"
                        )
                        logger.debug(f"Will delete entity: {existing_entity.id}")
                    else:
                        logger.warning(
                            f"Entity {existing_entity.id} not found in source but owned by "
                            f"different provider ({existing_entity.status.discovery_source})"
                        )
                else:
                    # If no status info, we can't determine ownership, so skip deletion
                    logger.warning(
                        f"Entity {existing_entity.id} not found in source but has no status info - skipping deletion"
                    )

        return creates, updates, deletes

    def _needs_update(self, current: Entity, existing: Entity) -> bool:
        """
        Check if entity needs updating by comparing fingerprints.

        Args:
            current: Entity from source system
            existing: Entity from graph

        Returns:
            True if entity needs updating
        """
        current_fingerprint = self._compute_fingerprint(current)
        existing_fingerprint = self._get_existing_fingerprint(existing)

        needs_update = current_fingerprint != existing_fingerprint

        # Debug logging for GitHub entities that are being updated unnecessarily
        if needs_update and current.kind in [
            "GithubRepository",
            "GithubHostingService",
        ]:
            logger.debug(
                f"Entity {current.id} needs update - current fingerprint: {current_fingerprint[:16]}..., existing: {existing_fingerprint[:16]}..."
            )

            # Log the actual content being fingerprinted for comparison
            if hasattr(current.spec, "to_dict"):
                current_spec = current.spec.to_dict()
            elif hasattr(current.spec, "model_dump"):
                current_spec = current.spec.model_dump()
            else:
                current_spec = current.spec

            logger.debug(f"Current spec content: {current_spec}")
            logger.debug(f"Current labels: {current.metadata.labels}")

        return needs_update

    def _get_existing_fingerprint(self, existing: Entity) -> str:
        """
        Extract fingerprint from existing entity, handling different annotation formats.

        Args:
            existing: Entity from graph with potentially different annotation format

        Returns:
            Fingerprint string, or empty string if not found
        """
        if not existing.metadata.annotations:
            return ""

        # Try different ways to access the fingerprint annotation
        try:
            # Method 1: Direct dict access (if annotations is a dict)
            if hasattr(existing.metadata.annotations, "get") and callable(
                existing.metadata.annotations.get
            ):
                return existing.metadata.annotations.get("fingerprint", "")

            # Method 2: additional_properties (Devgraph API response format)
            if hasattr(existing.metadata.annotations, "additional_properties"):
                if existing.metadata.annotations.additional_properties:
                    return existing.metadata.annotations.additional_properties.get(
                        "fingerprint", ""
                    )

            # Method 3: Direct item access (if annotations supports __getitem__)
            if hasattr(existing.metadata.annotations, "__getitem__"):
                try:
                    return existing.metadata.annotations["fingerprint"]
                except (KeyError, TypeError):
                    pass

            # Method 4: Check if fingerprint is a direct attribute
            if hasattr(existing.metadata.annotations, "fingerprint"):
                return existing.metadata.annotations.fingerprint

            # Method 5: Convert to dict if possible and then access
            if hasattr(existing.metadata.annotations, "to_dict"):
                annotations_dict = existing.metadata.annotations.to_dict()
                return annotations_dict.get("fingerprint", "")
            elif hasattr(existing.metadata.annotations, "model_dump"):
                annotations_dict = existing.metadata.annotations.model_dump()
                return annotations_dict.get("fingerprint", "")

        except Exception as e:
            logger.debug(
                f"Error extracting fingerprint from existing entity {existing.id}: {e}"
            )

        return ""

    def _compute_fingerprint(self, entity: Entity) -> str:
        """
        Compute a fingerprint for an entity based on its spec and relevant metadata.

        Args:
            entity: Entity to fingerprint

        Returns:
            SHA256 hash representing the entity's state
        """
        # Include spec and labels in fingerprint
        # Convert spec to dict if it has to_dict method (Pydantic models)
        if hasattr(entity.spec, "to_dict"):
            spec_dict = entity.spec.to_dict()
        elif hasattr(entity.spec, "model_dump"):
            spec_dict = entity.spec.model_dump()
        else:
            spec_dict = entity.spec

        content = {"spec": spec_dict, "labels": entity.metadata.labels}

        # Sort keys for consistent hashing
        content_str = json.dumps(content, sort_keys=True)
        fingerprint = hashlib.sha256(content_str.encode()).hexdigest()

        return fingerprint

    def _store_fingerprint(self, entity: Entity, fingerprint: str) -> None:
        """Store fingerprint in entity annotations.

        Args:
            entity: Entity to store fingerprint on
            fingerprint: Fingerprint hash to store
        """
        # Ensure annotations exist
        if not entity.metadata.annotations:
            entity.metadata.annotations = {}

        # Handle different types of annotations (dict vs EntityMetadataAnnotations)
        try:
            # Method 1: Direct dict assignment (most common for new entities)
            if hasattr(entity.metadata.annotations, "__setitem__"):
                entity.metadata.annotations["fingerprint"] = fingerprint
                return

            # Method 2: additional_properties (Devgraph API response format)
            if hasattr(entity.metadata.annotations, "additional_properties"):
                if not entity.metadata.annotations.additional_properties:
                    entity.metadata.annotations.additional_properties = {}
                entity.metadata.annotations.additional_properties["fingerprint"] = (
                    fingerprint
                )
                return

            # Method 3: Direct attribute assignment
            if hasattr(entity.metadata.annotations, "__dict__"):
                entity.metadata.annotations.fingerprint = fingerprint
                return

        except Exception as e:
            logger.debug(f"Error storing fingerprint on entity {entity.id}: {e}")
            # Fallback: try to convert annotations to dict
            try:
                if not isinstance(entity.metadata.annotations, dict):
                    entity.metadata.annotations = {"fingerprint": fingerprint}
                else:
                    entity.metadata.annotations["fingerprint"] = fingerprint
            except Exception as fallback_error:
                logger.warning(
                    f"Failed to store fingerprint on entity {entity.id}: {fallback_error}"
                )


class ReconcilingMoleculeProvider(MoleculeProvider, ABC):
    """Base class for providers that implement proper reconciliation."""

    def __init__(
        self,
        name: str,
        every: int,
        config,
        reconciliation_strategy: ReconciliationStrategy,
    ):
        """
        Initialize reconciling provider.

        Args:
            name: Provider name
            every: Reconciliation interval in seconds
            config: Provider configuration
            reconciliation_strategy: Strategy to use for reconciliation
        """
        super().__init__(name, every, config)
        self.reconciliation_strategy = reconciliation_strategy

    def _reconcile_entities(self, client: AuthenticatedClient) -> GraphMutations:
        """
        Reconcile entities using the configured strategy.

        Args:
            client: Authenticated Devgraph API client

        Returns:
            GraphMutations containing entities and relations to create/delete
        """
        try:
            logger.info(f"Starting reconciliation for provider {self.name}")

            # Step 1: Discover current entities from source
            logger.debug("Discovering current entities from source")
            current_entities = self._discover_current_entities()
            logger.info(f"Found {len(current_entities)} entities in source")

            # Step 2: Get existing entities from graph that belong to this provider
            logger.debug("Querying existing entities from graph")
            existing_entities = self._get_our_entities_from_graph(client)
            logger.info(f"Found {len(existing_entities)} existing entities in graph")

            # Step 3: Perform reconciliation
            logger.debug("Computing reconciliation")
            logger.debug(
                f"Current entities: {[f'{e.kind}:{e.metadata.name}' for e in current_entities]}"
            )
            logger.debug(
                f"Existing entities: {[f'{e.kind}:{e.metadata.name}' for e in existing_entities]}"
            )

            creates, updates, deletes = self.reconciliation_strategy.reconcile(
                current_entities, existing_entities, self.name
            )
            logger.debug(
                f"After reconciliation - Creates: {[f'{e.kind}:{e.metadata.name}' for e in creates]}"
            )
            logger.debug(
                f"After reconciliation - Updates: {[f'{e.kind}:{e.metadata.name}' for e in updates]}"
            )
            logger.debug(
                f"After reconciliation - Deletes: {[str(ref) for ref in deletes]}"
            )

            # Step 4: Reconcile relations first to find what needs to be created/deleted
            logger.debug("Reconciling relations")
            all_current_relations = self._create_relations_for_entities(
                current_entities
            )

            # Get existing relations from graph to compare
            from devgraph_client.api.entities import get_entities

            resp = get_entities.sync_detailed(
                client=client,
                limit=10000,
                # include_relations defaults to True - we need them for reconciliation
            )

            existing_relations_in_graph = []
            if resp.status_code == 200 and resp.parsed and resp.parsed.relations:
                existing_relations_in_graph = resp.parsed.relations

            # Find missing relations (should exist but don't)
            existing_relation_sigs = set()
            for rel in existing_relations_in_graph:
                sig = self._get_relation_signature(rel)
                existing_relation_sigs.add(sig)

            relations_to_create = []
            for rel in all_current_relations:
                sig = self._get_relation_signature(rel)
                if sig not in existing_relation_sigs:
                    relations_to_create.append(rel)
                    logger.debug(f"Missing relation to create: {sig}")

            # Find stale relations (exist but shouldn't)
            current_relation_sigs = {
                self._get_relation_signature(r) for r in all_current_relations
            }
            stale_relations = []
            for existing_rel in existing_relations_in_graph:
                existing_sig = self._get_relation_signature(existing_rel)

                # Check if this relation involves entities managed by this provider
                source_managed = self._is_entity_managed_by_provider(
                    existing_rel.source,
                    (
                        resp.parsed.primary_entities
                        if resp.parsed.primary_entities
                        else []
                    ),
                )
                target_managed = self._is_entity_managed_by_provider(
                    existing_rel.target,
                    (
                        resp.parsed.primary_entities
                        if resp.parsed.primary_entities
                        else []
                    ),
                )

                # Only manage relations where at least one end is managed by this provider
                if (
                    source_managed or target_managed
                ) and existing_sig not in current_relation_sigs:
                    logger.info(f"Found stale relation to delete: {existing_sig}")
                    from devgraph_integrations.types.entities import (
                        EntityReference,
                        EntityRelation,
                    )

                    entity_relation = EntityRelation(
                        source=EntityReference(
                            apiVersion=existing_rel.source.api_version,
                            kind=existing_rel.source.kind,
                            name=existing_rel.source.name,
                        ),
                        target=EntityReference(
                            apiVersion=existing_rel.target.api_version,
                            kind=existing_rel.target.kind,
                            name=existing_rel.target.name,
                        ),
                        relation=existing_rel.relation,
                        namespace=existing_rel.namespace,
                    )
                    stale_relations.append(entity_relation)

            logger.info(f"Found {len(relations_to_create)} missing relations to create")
            logger.info(f"Found {len(stale_relations)} stale relations to delete")

            logger.info(
                f"Reconciliation complete - Creates: {len(creates)}, "
                f"Updates: {len(updates)}, Deletes: {len(deletes)}, "
                f"Relations to create: {len(relations_to_create)}, Stale relations: {len(stale_relations)}"
            )

            return GraphMutations(
                create_entities=creates + updates,
                delete_entities=deletes,
                create_relations=relations_to_create,
                delete_relations=stale_relations,
            )

        except Exception as e:
            logger.error(f"Reconciliation failed for provider {self.name}: {e}")
            logger.exception("Reconciliation error details")
            # Return empty mutations to avoid partial state
            return self._get_empty_mutations()

    @abstractmethod
    def _discover_current_entities(self) -> List[Entity]:
        """
        Discover all entities that should currently exist according to the source system.

        Returns:
            List of entities that represent the current desired state
        """
        pass

    def _get_our_entities_from_graph(self, client: AuthenticatedClient) -> List[Entity]:
        """
        Get entities from the graph that belong to this provider.

        Args:
            client: Authenticated Devgraph API client

        Returns:
            List of entities owned by this provider
        """
        try:
            # Get all entities managed by this provider
            # Note: namespace is already specified via the graph name, no need to filter
            # Don't fetch relations - we only need entity metadata for reconciliation
            resp = get_entities.sync_detailed(
                client=client,
                limit=10000,  # Get all entities for this provider
                include_relations=False,  # Skip relations for performance
            )

            all_entities = []
            if resp.status_code == 200 and resp.parsed and resp.parsed.primary_entities:
                # Get entity kinds managed by this provider
                managed_kinds = self._get_managed_entity_kinds()

                for entity in resp.parsed.primary_entities:
                    # Filter to only entities that could be created by this provider
                    if entity.kind in managed_kinds:
                        # Convert API client EntityResponse to domain Entity
                        from devgraph_integrations.types.entities import Entity

                        try:
                            domain_entity = Entity.model_validate(entity.to_dict())

                            # CRITICAL: Only include entities that were actually created by this provider
                            # This prevents providers from trying to manage entities created by other providers
                            if (
                                hasattr(domain_entity, "status")
                                and hasattr(domain_entity.status, "discovery_source")
                                and domain_entity.status.discovery_source == self.name
                            ):
                                # Additional validation: Check if entity has required metadata
                                # Ghost/stale entities from buggy queries may be missing critical fields
                                if (
                                    hasattr(domain_entity, "metadata")
                                    and hasattr(domain_entity.metadata, "name")
                                    and domain_entity.metadata.name
                                    and hasattr(domain_entity, "kind")
                                    and domain_entity.kind
                                ):
                                    all_entities.append(domain_entity)
                                    logger.debug(
                                        f"Including entity owned by this provider: {domain_entity.id}"
                                    )
                                else:
                                    logger.warning(
                                        f"Skipping malformed entity (missing metadata): {getattr(domain_entity, 'id', 'unknown')}"
                                    )
                            else:
                                discovery_source = getattr(
                                    getattr(domain_entity, "status", None),
                                    "discovery_source",
                                    "unknown",
                                )
                                logger.debug(
                                    f"Skipping entity not owned by this provider: {domain_entity.id} "
                                    f"(owned by: {discovery_source}, we are: {self.name})"
                                )

                        except Exception as conversion_error:
                            logger.error(
                                f"Failed to convert API entity to domain entity: {conversion_error}"
                            )
                            logger.debug(f"Entity data: {entity.to_dict()}")
                            # Skip this entity and continue with others
                            continue

            return all_entities

        except Exception as e:
            logger.error(
                f"Error querying existing entities for provider {self.name}: {e}"
            )
            return []

    @abstractmethod
    def _get_managed_entity_kinds(self) -> List[str]:
        """
        Get list of entity kinds managed by this provider.

        Returns:
            List of entity kind strings (e.g., ['LdapUser', 'LdapGroup'])
        """
        pass

    def _create_relations_for_entities(self, entities: List[Entity]) -> List:
        """
        Create relations for the given entities.

        Default implementation returns empty list. Override to add relations.

        Args:
            entities: Entities to create relations for

        Returns:
            List of relation objects
        """
        return []

    def _reconcile_relations(
        self, client: AuthenticatedClient, current_relations: List
    ) -> List:
        """
        Reconcile relations by comparing current desired relations with existing relations in the graph.

        Args:
            client: Authenticated Devgraph API client
            current_relations: Relations that should currently exist

        Returns:
            List of relations that should be deleted (exist in graph but not in current)
        """
        try:
            from devgraph_client.api.entities import get_entities

            logger.info(f"Starting relation reconciliation for provider {self.name}")

            # Get all entities for this provider to extract their relations
            # Note: namespace is already specified via the graph name, no need to filter
            resp = get_entities.sync_detailed(
                client=client,
                limit=10000,
            )

            if resp.status_code != 200 or not resp.parsed:
                logger.warning(
                    f"Failed to fetch entities for relation reconciliation: status={resp.status_code}"
                )
                return []

            logger.info(
                f"Fetched {len(resp.parsed.primary_entities) if resp.parsed.primary_entities else 0} entities"
            )
            logger.info(
                f"Fetched {len(resp.parsed.relations) if resp.parsed.relations else 0} existing relations"
            )

            # Build a set of current relation signatures for quick lookup
            current_relation_sigs = set()
            for rel in current_relations:
                sig = self._get_relation_signature(rel)
                current_relation_sigs.add(sig)
                logger.debug(f"Current relation: {sig}")

            logger.info(f"Current desired relations: {len(current_relation_sigs)}")

            # Collect existing relations from the graph
            stale_relations = []
            if resp.parsed.relations:
                for existing_rel in resp.parsed.relations:
                    existing_sig = self._get_relation_signature(existing_rel)
                    logger.debug(f"Checking existing relation: {existing_sig}")

                    # Check if this relation is managed by this provider using ownership metadata
                    managed_by = ""
                    if hasattr(existing_rel, "metadata") and hasattr(existing_rel.metadata, "labels"):
                        managed_by = existing_rel.metadata.labels.get("managed-by", "")

                    provider_managed = managed_by == f"provider:{self.name}"

                    logger.debug(f"  Relation managed-by: {managed_by}, Provider: {self.name}, Match: {provider_managed}")

                    # Only manage relations that this provider owns
                    if not provider_managed:
                        logger.debug(
                            f"  Skipping - not managed by provider:{self.name}"
                        )
                        continue

                    # If relation exists in graph but not in current desired state, mark for deletion
                    if existing_sig not in current_relation_sigs:
                        logger.info(f"Found stale relation to delete: {existing_sig}")
                        # Convert the API relation format to EntityRelation format for deletion
                        from devgraph_integrations.types.entities import (
                            EntityReference,
                            EntityRelation,
                        )

                        try:
                            entity_relation = EntityRelation(
                                source=EntityReference(
                                    apiVersion=existing_rel.source.api_version,
                                    kind=existing_rel.source.kind,
                                    name=existing_rel.source.name,
                                ),
                                target=EntityReference(
                                    apiVersion=existing_rel.target.api_version,
                                    kind=existing_rel.target.kind,
                                    name=existing_rel.target.name,
                                ),
                                relation=existing_rel.relation,
                                namespace=existing_rel.namespace,
                            )
                            stale_relations.append(entity_relation)
                            logger.debug(
                                f"  Converted relation for deletion: {entity_relation}"
                            )
                        except Exception as conv_error:
                            logger.error(
                                f"Failed to convert relation for deletion: {conv_error}"
                            )
                            logger.debug(f"  Existing relation: {existing_rel}")
                    else:
                        logger.debug("  Keeping - still in desired state")

            logger.info(
                f"Relation reconciliation complete: {len(stale_relations)} stale relations to delete"
            )
            return stale_relations

        except Exception as e:
            logger.error(f"Error reconciling relations: {e}")
            logger.exception("Relation reconciliation error details")
            return []

    def _get_relation_signature(self, relation) -> str:
        """
        Get a unique signature for a relation including ownership metadata.

        Args:
            relation: Relation object

        Returns:
            Unique string signature including managed-by label
        """
        # Handle different relation formats
        if (
            hasattr(relation, "source")
            and hasattr(relation, "target")
            and hasattr(relation, "relation")
        ):
            source_id = (
                relation.source.id
                if hasattr(relation.source, "id")
                else str(relation.source)
            )
            target_id = (
                relation.target.id
                if hasattr(relation.target, "id")
                else str(relation.target)
            )

            # Include managed-by label in signature for ownership tracking
            managed_by = ""
            if hasattr(relation, "metadata") and hasattr(relation.metadata, "labels"):
                managed_by = relation.metadata.labels.get("managed-by", "")

            return f"{source_id}::{relation.relation}::{target_id}::{managed_by}"
        return str(relation)

    def _is_entity_managed_by_provider(self, entity_ref, primary_entities) -> bool:
        """
        Check if an entity reference belongs to entities managed by this provider.

        Args:
            entity_ref: Entity reference to check
            primary_entities: List of primary entities from the graph

        Returns:
            True if entity is managed by this provider
        """
        entity_id = entity_ref.id if hasattr(entity_ref, "id") else str(entity_ref)

        for entity in primary_entities:
            if entity.id == entity_id:
                # Check if entity belongs to this provider
                if (
                    hasattr(entity, "status")
                    and hasattr(entity.status, "discovery_source")
                    and entity.status.discovery_source == self.name
                ):
                    return True
                break

        return False

    def create_relation_with_metadata(
        self,
        relation_class,
        source: "EntityReference",
        target: "EntityReference",
        namespace: str = "default",
        spec: dict = None,
        **kwargs
    ):
        """
        Helper method to create a relation with proper ownership metadata.

        Args:
            relation_class: The relation class to instantiate (e.g., PersonMemberOfTeamRelation)
            source: Source entity reference
            target: Target entity reference
            namespace: Namespace for the relation
            spec: Optional spec dict or typed spec object
            **kwargs: Additional arguments passed to relation constructor

        Returns:
            Relation instance with ownership metadata

        Example:
            relation = self.create_relation_with_metadata(
                PersonMemberOfTeamRelation,
                source=person.reference,
                target=team.reference,
                spec={"role": "member"}
            )
        """
        from devgraph_integrations.types.entities import RelationMetadata

        # Create metadata with ownership tracking
        metadata = RelationMetadata(
            labels={
                "managed-by": f"provider:{self.name}",
                "source-type": "discovered",
            },
            annotations={}
        )

        # Merge any additional metadata from kwargs
        if "metadata" in kwargs:
            user_metadata = kwargs.pop("metadata")
            if hasattr(user_metadata, "labels"):
                metadata.labels.update(user_metadata.labels)
            if hasattr(user_metadata, "annotations"):
                metadata.annotations.update(user_metadata.annotations)

        # Create the relation
        return relation_class(
            source=source,
            target=target,
            namespace=namespace,
            metadata=metadata,
            spec=spec or {},
            **kwargs
        )


class IncrementalReconciliation(ReconciliationStrategy):
    """Incremental reconciliation for systems that support change detection."""

    def __init__(self):
        """Initialize incremental reconciliation strategy."""
        pass

    def get_entity_key(self, entity) -> str:
        """Get unique key for entity using its ID."""
        return entity.id

    def reconcile(
        self,
        current_entities: List[Entity],
        existing_entities: List[Entity],
        provider_name: str,
    ) -> Tuple[List[Entity], List[Entity], List[EntityReference]]:
        """
        Perform incremental reconciliation.

        Note: This is a simplified version. Full implementation would need
        change detection support from the source system.
        """
        # For now, delegate to full reconciliation
        # TODO: Implement proper incremental logic with change detection
        full_reconciler = FullStateReconciliation()
        return full_reconciler.reconcile(
            current_entities, existing_entities, provider_name
        )
