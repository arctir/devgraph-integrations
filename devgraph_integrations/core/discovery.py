import json
import threading
import time
from time import sleep

import requests  # type: ignore
import schedule
from devgraph_client.api.entities import (
    create_entities_bulk,
    create_entity,
    create_entity_definition,
    create_entity_relation,
    create_entity_relations_bulk,
    delete_entity,
    delete_entity_relation,
    get_entities,
)
from devgraph_client.client import (
    AuthenticatedClient,
)
from devgraph_client.models.bulk_entity_relation_create_request import (
    BulkEntityRelationCreateRequest,
)
from devgraph_client.models.entity_definition_spec import EntityDefinitionSpec
from loguru import logger

from devgraph_integrations.config import Config
from devgraph_integrations.core.extension import DiscoveryExtensionManager
from devgraph_integrations.core.provider import Provider
from devgraph_integrations.core.registry import (
    auto_discover_all_definitions,
    create_all_definitions,
)
from devgraph_integrations.types.entities import (
    Entity,
    EntityReference,
    EntityRelation,
    FieldSelectedEntityRelation,
)


def run_threaded(job_func):
    thread = threading.Thread(target=job_func)
    thread.start()


def log_client_error(response):
    try:
        body = json.loads(response.content)
        detail = body.get("detail", "No detail provided")
        logger.error(f"Request failed with status: {response.status_code}: {detail}")
    except (json.JSONDecodeError, AttributeError):
        # Handle non-JSON responses or empty content
        content_str = getattr(response, "content", b"").decode("utf-8", errors="ignore")
        logger.error(
            f"Request failed with status: {response.status_code}. "
            f"Response content: {content_str[:200] if content_str else '(empty)'}"
        )


def resolve_field_selector_to_entities(
    field_selector, api_client: AuthenticatedClient
) -> list[EntityReference]:
    """
    Resolve a FieldSelector to a list of matching EntityReference objects.

    Args:
        field_selector: FieldSelector with field, value, and optional entity_type constraints
        api_client: Authenticated client for API calls

    Returns:
        List of EntityReference objects that match the field selector
    """
    try:
        # Build the field selector string for the API call
        selector_string = field_selector.to_string()

        logger.debug(f"Resolving field selector: {selector_string}")

        # Query entities using the field selector
        # Exclude relations for faster queries - we only need entity references
        # Using modest limit - field selectors should be specific enough to match < 100 entities
        resp = get_entities.sync_detailed(
            client=api_client,
            field_selector=selector_string,
            limit=100,  # Reasonable limit for field selector matches
            include_relations=False,  # Skip relations for performance
        )

        if resp.status_code != 200:
            logger.error(f"Failed to resolve field selector: {resp.status_code}")
            return []

        result_set = resp.parsed
        if not result_set or not result_set.primary_entities:
            logger.debug(f"No entities found for field selector: {selector_string}")
            return []

        # Convert to EntityReference objects and apply entity type filtering
        entity_refs = []
        for entity in result_set.primary_entities:
            entity_ref = EntityReference(
                apiVersion=entity.api_version,
                kind=entity.kind,
                name=entity.name,
                namespace=entity.namespace,
            )

            # FIXME
            # Apply entity type constraints if specified
            # print(field_selector.entity_type)
            # print(entity_ref)
            # if field_selector.entity_type:
            #     if not field_selector.entity_type.matches(entity_ref):
            #         logger.debug(
            #             f"Entity {entity_ref.id} filtered out by type constraints"
            #         )
            #         continue

            entity_refs.append(entity_ref)

        # Warn if we hit the limit - might be truncated results
        if len(entity_refs) >= 100:
            logger.warning(
                f"Field selector matched {len(entity_refs)} entities (limit reached). "
                f"Results may be truncated. Consider using a more specific selector: {selector_string}"
            )

        logger.debug(
            f"Resolved {len(entity_refs)} entities for field selector: {selector_string}"
        )
        return entity_refs

    except Exception as e:
        logger.error(f"Error resolving field selector: {e}")
        return []


def resolve_field_selected_relations(
    field_selected_relations: list[FieldSelectedEntityRelation],
    api_client: AuthenticatedClient,
) -> list[EntityRelation]:
    """
    Resolve FieldSelectedEntityRelation objects to concrete EntityRelation objects.

    Args:
        field_selected_relations: List of FieldSelectedEntityRelation objects to resolve
        api_client: Authenticated client for API calls

    Returns:
        List of concrete EntityRelation objects with resolved source/target references
    """
    resolved_relations = []

    for field_relation in field_selected_relations:
        logger.debug(f"Resolving field-selected relation: {field_relation.relation}")

        # Determine source entities
        source_entities = []
        if field_relation.source_selector:
            # Resolve source using field selector
            source_entities = resolve_field_selector_to_entities(
                field_relation.source_selector, api_client
            )
        elif field_relation.source:
            # Use explicit source
            source_entities = [field_relation.source]
        else:
            logger.warning("Field-selected relation has no source or source_selector")
            continue

        # Determine target entities
        target_entities = []
        if field_relation.target_selector:
            # Resolve target using field selector
            target_entities = resolve_field_selector_to_entities(
                field_relation.target_selector, api_client
            )
        elif field_relation.target:
            # Use explicit target
            target_entities = [field_relation.target]
        else:
            logger.warning("Field-selected relation has no target or target_selector")
            continue

        # Create concrete relations for all source/target combinations
        for source_ref in source_entities:
            for target_ref in target_entities:
                concrete_relation = EntityRelation(
                    namespace=field_relation.namespace,
                    relation=field_relation.relation,
                    source=source_ref,
                    target=target_ref,
                )
                resolved_relations.append(concrete_relation)
                logger.debug(
                    f"Created relation: {source_ref.kind}/{source_ref.name} "
                    f"--{field_relation.relation}--> {target_ref.kind}/{target_ref.name}"
                )

    logger.info(
        f"Resolved {len(resolved_relations)} concrete relations from {len(field_selected_relations)} field-selected relations"
    )
    return resolved_relations


def get_existing_entities_for_provider(
    provider: Provider, api_client: AuthenticatedClient
) -> list[EntityReference]:
    """
    Get all existing entities in the graph that were created by this provider.
    Uses pagination to handle large numbers of entities efficiently.

    Args:
        provider: The provider to get entities for
        api_client: Authenticated client for API calls

    Returns:
        List of EntityReference objects for entities owned by this provider
    """
    existing_entities = []
    page_size = 100  # Modest page size for efficient queries
    offset = 0
    entity_defs = [ed.kind for ed in provider.entity_definitions()]

    try:
        while True:
            # Query entities using pagination
            # Exclude relations for faster queries - we only need entity references
            # Note: namespace is already specified via the graph name, no need to filter
            resp = get_entities.sync_detailed(
                client=api_client,
                limit=page_size,
                offset=offset,
                include_relations=False,  # Skip relations for performance
            )

            if resp.status_code != 200:
                logger.error(f"Failed to fetch entities: status {resp.status_code}")
                break

            if not resp.parsed or not resp.parsed.primary_entities:
                # No more entities to fetch
                break

            # Process this page of entities
            page_count = 0
            for entity in resp.parsed.primary_entities:
                # Filter to only entities that could be created by this provider
                if entity.kind in entity_defs:
                    entity_ref = EntityReference(
                        apiVersion=entity.api_version,
                        kind=entity.kind,
                        name=entity.name,
                        namespace=entity.namespace,
                    )
                    existing_entities.append(entity_ref)
                    page_count += 1

            logger.debug(
                f"Fetched page at offset {offset}: {len(resp.parsed.primary_entities)} entities, "
                f"{page_count} matched provider types"
            )

            # Check if we got a full page - if not, we're done
            if len(resp.parsed.primary_entities) < page_size:
                break

            offset += page_size

        logger.info(
            f"Found {len(existing_entities)} existing entities for provider {provider.name} "
            f"across {(offset // page_size) + 1} pages"
        )
        return existing_entities

    except Exception as e:
        logger.error(
            f"Error getting existing entities for provider {provider.name}: {e}"
        )
        return []


def create_meta_type_relations(
    provider, entities: list[Entity]
) -> tuple[list[Entity], list]:
    """
    Create meta type entities and IS_A relations between entities and their meta types.

    Args:
        provider: The provider that created the entities
        entities: List of entities to create meta relations for

    Returns:
        Tuple of (meta_entities, relations) for entities that have meta_type alignment
    """
    from devgraph_client.models.entity_reference import (
        EntityReference,
    )
    from devgraph_client.models.entity_relation import (
        EntityRelation,
    )

    relations = []
    meta_entities = []
    created_meta_types = set()  # Track which meta entities we've already created

    # Get entity definitions from provider
    try:
        entity_definitions = provider.entity_definitions()
    except Exception as e:
        logger.debug(
            f"Could not get entity definitions from provider {provider.name}: {e}"
        )
        return meta_entities, relations

    # Build a mapping of entity kind -> meta_type
    kind_to_meta_type = {}
    for definition in entity_definitions:
        if hasattr(definition, "meta_type") and definition.meta_type:
            kind_to_meta_type[definition.kind] = definition.meta_type

    if not kind_to_meta_type:
        logger.debug(f"No meta type mappings found for provider {provider.name}")
        return meta_entities, relations

    logger.debug(f"Found meta type mappings: {kind_to_meta_type}")
    logger.debug(f"Processing {len(entities)} entities for meta type relations")

    # Import meta type entities (used in string comparison below)

    # Create meta entities and IS_A relations for entities that have meta type alignment
    for entity in entities:
        meta_type = kind_to_meta_type.get(entity.kind)
        logger.debug(
            f"Entity {entity.kind}/{entity.metadata.name} -> meta_type: {meta_type}"
        )
        if meta_type:
            # Create meta entity if we haven't already
            if meta_type not in created_meta_types:
                try:
                    # Create the meta type entity using the actual meta type spec
                    if meta_type == "Team":
                        from devgraph_integrations.types.meta import (
                            V1TeamEntity,
                            V1TeamEntitySpec,
                        )

                        meta_entity = V1TeamEntity(
                            apiVersion="entities.devgraph.ai/v1",
                            kind="Team",
                            metadata={
                                "name": "team",
                                "namespace": entity.metadata.namespace,
                            },
                            spec=V1TeamEntitySpec(
                                display_name="Team",
                                description="Base meta type for teams and organizations",
                            ),
                        )
                    elif meta_type == "Workstream":
                        from devgraph_integrations.types.meta import (
                            V1ProjectEntity,
                            V1ProjectEntitySpec,
                        )
                        from devgraph_integrations.types.meta.v1_project import (
                            ProjectType,
                        )

                        meta_entity = V1ProjectEntity(
                            apiVersion="entities.devgraph.ai/v1",
                            kind="Workstream",
                            metadata={
                                "name": "workstream",
                                "namespace": entity.metadata.namespace,
                            },
                            spec=V1ProjectEntitySpec(
                                project_type=ProjectType.OTHER,
                                name="Workstream",
                                description="Base meta type for workstreams and initiatives",
                            ),
                        )
                    else:
                        logger.warning(f"Unknown meta type: {meta_type}")
                        continue

                    meta_entities.append(meta_entity)
                    created_meta_types.add(meta_type)
                    logger.debug(f"Created meta entity: {meta_type}")

                except Exception as e:
                    logger.warning(f"Failed to create meta entity {meta_type}: {e}")
                    continue

            # Create IS_A relation: entity IS_A meta_type
            try:
                relation = EntityRelation(
                    relation="IS_A",
                    source=EntityReference(
                        api_version=entity.apiVersion,
                        kind=entity.kind,
                        name=entity.metadata.name,
                        namespace=entity.metadata.namespace,
                    ),
                    target=EntityReference(
                        api_version="entities.devgraph.ai/v1",
                        kind=meta_type,
                        name=meta_type.lower(),
                        namespace=entity.metadata.namespace,
                    ),
                    namespace=entity.metadata.namespace,
                )
                relations.append(relation)
                logger.debug(
                    f"Created IS_A relation: {entity.kind}/{entity.metadata.name} IS_A {meta_type}"
                )
            except Exception as e:
                logger.warning(f"Failed to create IS_A relation for {entity.id}: {e}")

    logger.debug(
        f"Meta type relations summary: created {len(meta_entities)} meta entities, {len(relations)} IS_A relations"
    )
    return meta_entities, relations


def compute_entity_deletions(
    existing_entities: list[EntityReference],
    desired_entities: list[Entity],
) -> list[EntityReference]:
    """
    Compute which entities should be deleted by comparing existing vs desired state.

    Args:
        existing_entities: Currently existing entities in the graph
        desired_entities: Entities that should exist according to provider

    Returns:
        List of EntityReference objects that should be deleted
    """
    # Convert desired entities to references for comparison
    desired_refs = set()
    for entity in desired_entities:
        ref_id = f"{entity.apiVersion}/{entity.kind}/{entity.namespace}/{entity.name}"
        desired_refs.add(ref_id)

    # Find existing entities that are not in desired state
    entities_to_delete = []
    for existing_ref in existing_entities:
        existing_id = f"{existing_ref.apiVersion}/{existing_ref.kind}/{existing_ref.namespace}/{existing_ref.name}"
        if existing_id not in desired_refs:
            entities_to_delete.append(existing_ref)

    logger.info(f"Computed {len(entities_to_delete)} entities for deletion")
    return entities_to_delete


def run_provider(
    provider: Provider, api_client: AuthenticatedClient, environment_id: str = None
):
    def wrapped():
        # Note: environment_id parameter is available but currently unused
        logger.debug(f"Running provider: {provider}")

        # Get current state from provider
        mutations = provider.reconcile(api_client)

        # For providers that implement their own reconciliation (ReconcilingMoleculeProvider),
        # skip the legacy deletion computation as they handle deletions internally
        from devgraph_integrations.core.provider import DefinitionOnlyProvider
        from devgraph_integrations.molecules.base.reconciliation import (
            ReconcilingMoleculeProvider,
        )

        if not isinstance(
            provider, (ReconcilingMoleculeProvider, DefinitionOnlyProvider)
        ):
            # Get existing entities for state reconciliation
            existing_entities = get_existing_entities_for_provider(provider, api_client)

            # Compute what needs to be deleted
            entities_to_delete = compute_entity_deletions(
                existing_entities, mutations.create_entities
            )

            # Add computed deletions to mutations
            mutations.delete_entities.extend(entities_to_delete)
        else:
            if isinstance(provider, ReconcilingMoleculeProvider):
                logger.debug(
                    f"Provider {provider.name} uses ReconcilingMoleculeProvider - skipping legacy deletion computation"
                )
            elif isinstance(provider, DefinitionOnlyProvider):
                logger.debug(
                    f"Provider {provider.name} is definition-only - skipping legacy deletion computation"
                )

        # Create meta type entities and IS_A relations for entities with meta_type alignment
        if isinstance(provider, ReconcilingMoleculeProvider):
            # For reconciling providers, get all current entities to ensure all have IS_A relations
            try:
                current_entities = provider._discover_current_entities()
            except Exception as e:
                logger.warning(f"Failed to get current entities for meta type relations: {e}")
                current_entities = []
            meta_entities, meta_relations = create_meta_type_relations(
                provider, current_entities
            )
        else:
            # For legacy providers, only create IS_A relations for entities being created
            meta_entities, meta_relations = create_meta_type_relations(
                provider, mutations.create_entities
            )

        mutations.create_entities.extend(meta_entities)
        mutations.create_relations.extend(meta_relations)

        # Log reconciliation summary
        logger.info(f"Provider {provider.name} reconciliation summary:")
        logger.info(f"  - Entities to create/update: {len(mutations.create_entities)}")
        logger.info(f"  - Entities to delete: {len(mutations.delete_entities)}")
        logger.info(f"  - Relations to create: {len(mutations.create_relations)}")
        logger.info(f"  - Relations to delete: {len(mutations.delete_relations)}")
        if meta_entities:
            logger.info(f"  - Meta type entities: {len(meta_entities)}")
        if meta_relations:
            logger.info(f"  - Meta type IS_A relations: {len(meta_relations)}")

        # Process entity deletions first to avoid orphaned relations
        for entity_ref in mutations.delete_entities:
            logger.debug(f"Deleting stale entity: {entity_ref.kind}/{entity_ref.name}")
            try:
                resp = delete_entity.sync_detailed(
                    client=api_client,
                    group=entity_ref.apiVersion.split("/")[0],
                    version=entity_ref.apiVersion.split("/")[1],
                    kind=entity_ref.kind,
                    namespace=entity_ref.namespace,
                    name=entity_ref.name,
                )
                if resp.status_code == 204:
                    logger.info(f"Successfully deleted entity: {entity_ref.id}")
                else:
                    logger.error(
                        f"Failed to delete entity {entity_ref.id}: {resp.status_code}"
                    )
                    log_client_error(resp)
            except Exception as e:
                logger.error(f"Error deleting entity {entity_ref.id}: {e}")

        # Process entity creations/updates using bulk API
        if mutations.create_entities:
            # Mark all entities as updated by this provider
            for entity in mutations.create_entities:
                entity.mark_updated(source=provider.name)

            # Group entities by their API definition (group/version/namespace/plural)
            # This allows us to use the bulk API efficiently
            entities_by_definition = {}
            for entity in mutations.create_entities:
                key = (entity.group, entity.version, entity.namespace, entity.plural)
                if key not in entities_by_definition:
                    entities_by_definition[key] = []
                entities_by_definition[key].append(entity)

            logger.info(
                f"Creating {len(mutations.create_entities)} entities using bulk API "
                f"({len(entities_by_definition)} entity types)"
            )

            # Process each entity definition group using bulk API
            total_created = 0
            total_failed = 0
            for (
                group,
                version,
                namespace,
                plural,
            ), entities in entities_by_definition.items():
                logger.info(
                    f"Creating {len(entities)} entities of type {group}/{version}/{plural} "
                    f"in namespace {namespace}"
                )

                # Use bulk endpoint for efficient entity creation with retry on rate limit
                max_retries = 3
                retry_delay = 1  # Start with 1 second

                for attempt in range(max_retries):
                    try:
                        resp = create_entities_bulk.sync_detailed(
                            client=api_client,
                            group=group,
                            version=version,
                            namespace=namespace,
                            plural=plural,
                            body=entities,
                        )

                        if resp.status_code == 201:
                            result = resp.parsed
                            # Access additional_properties dict for the response data
                            created = result.additional_properties.get(
                                "created_count", 0
                            )
                            failed = result.additional_properties.get("failed_count", 0)
                            total_created += created
                            total_failed += failed
                            logger.info(
                                f"Bulk creation result: {created} created, {failed} failed"
                            )

                            # Log any failures
                            failed_entities = result.additional_properties.get(
                                "failed_entities", []
                            )
                            if failed > 0 and failed_entities:
                                for failure in failed_entities[:5]:  # Log first 5
                                    logger.error(
                                        f"Failed to create entity: {failure.get('entity', 'unknown')}: "
                                        f"{failure.get('error', 'unknown error')}"
                                    )
                                if failed > 5:
                                    logger.error(f"... and {failed - 5} more failures")
                            break  # Success, exit retry loop

                        elif resp.status_code == 503:
                            # Rate limited - retry with exponential backoff
                            if attempt < max_retries - 1:
                                logger.warning(
                                    f"Rate limited (503), retrying in {retry_delay}s "
                                    f"(attempt {attempt + 1}/{max_retries})"
                                )
                                sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                                continue
                            else:
                                logger.error(
                                    f"Rate limited after {max_retries} attempts, giving up on this batch"
                                )
                                total_failed += len(entities)
                                break

                        elif resp.status_code == 404:
                            # Entity definition missing - try to create it and retry once
                            # Log the error to understand what's missing
                            log_client_error(resp)

                            # Only try to create definitions once per batch
                            if attempt == 0:
                                logger.warning(
                                    f"Entity definition missing (404), attempting to create definitions for provider {provider.name}"
                                )
                                try:
                                    created_any = False
                                    for entity_definition in provider.entity_definitions():
                                        # Convert to API model
                                        api_spec = EntityDefinitionSpec.from_dict(entity_definition.to_dict())
                                        def_resp = create_entity_definition.sync_detailed(
                                            client=api_client,
                                            body=api_spec,
                                        )
                                        if def_resp.status_code == 201:
                                            logger.info(f"Created missing entity definition: {entity_definition.kind}")
                                            created_any = True
                                        elif def_resp.status_code == 409:
                                            logger.debug(f"Entity definition already exists: {entity_definition.kind}")
                                        else:
                                            logger.warning(f"Failed to create entity definition: {def_resp.status_code}")
                                            log_client_error(def_resp)

                                    # Only retry if we actually created a new definition
                                    if created_any:
                                        logger.info("Created new entity definitions, retrying bulk creation")
                                        continue
                                    else:
                                        logger.warning("Entity definitions already exist, 404 error is from something else")
                                        total_failed += len(entities)
                                        break
                                except Exception as e:
                                    logger.error(f"Failed to create entity definitions: {e}")
                                    total_failed += len(entities)
                                    break
                            else:
                                logger.error("Still getting 404 after creating entity definitions, giving up")
                                total_failed += len(entities)
                                break
                        else:
                            logger.error(
                                f"Bulk entity creation failed with status {resp.status_code}"
                            )
                            log_client_error(resp)
                            total_failed += len(entities)
                            break  # Don't retry other errors

                    except Exception as bulk_error:
                        # Bulk endpoint failed, fall back to one-by-one
                        logger.warning(
                            f"Bulk entity creation failed: {bulk_error}, "
                            f"falling back to one-by-one creation for {len(entities)} entities"
                        )
                        # Fallback to one-by-one entity creation
                        for entity in entities:
                            resp = create_entity.sync_detailed(
                                client=api_client,
                                group=entity.group,
                                version=entity.version,
                                namespace=entity.namespace,
                                plural=entity.plural,
                                body=entity,
                            )
                            if resp.status_code == 201:
                                total_created += 1
                            else:
                                total_failed += 1
                                log_client_error(resp)
                        break  # Exit retry loop after fallback

            logger.info(
                f"Entity creation complete: {total_created} created, {total_failed} failed"
            )

        # Separate field-selected relations from standard relations
        standard_relations = []
        field_selected_relations = []

        for relation in mutations.create_relations:
            if isinstance(relation, FieldSelectedEntityRelation):
                field_selected_relations.append(relation)
            else:
                standard_relations.append(relation)

        # Resolve field-selected relations to concrete relations
        if field_selected_relations:
            logger.info(
                f"Resolving {len(field_selected_relations)} field-selected relations"
            )
            resolved_relations = resolve_field_selected_relations(
                field_selected_relations, api_client
            )
            standard_relations.extend(resolved_relations)

        # Process relation deletions
        for relation in mutations.delete_relations:
            if isinstance(relation, FieldSelectedEntityRelation):
                logger.debug(
                    f"Skipping field-selected relation deletion (not yet supported): {relation.relation}"
                )
                # TODO: Implement field-selected relation deletion
                continue

            logger.debug(
                f"Deleting stale relation: {relation.source.kind}/{relation.source.name} --{relation.relation}--> {relation.target.kind}/{relation.target.name}"
            )
            try:
                resp = delete_entity_relation.sync_detailed(
                    client=api_client,
                    namespace=relation.namespace,
                    body=relation,
                )
                if resp.status_code == 204:
                    logger.info(f"Successfully deleted relation: {relation.relation}")
                else:
                    logger.error(
                        f"Failed to delete relation {relation.relation}: {resp.status_code}"
                    )
                    log_client_error(resp)
            except Exception as e:
                logger.error(f"Error deleting relation {relation.relation}: {e}")

        # Create all concrete relations in the graph using bulk API
        if standard_relations:
            # Group relations by namespace for bulk creation
            relations_by_namespace = {}
            for relation in standard_relations:
                namespace = relation.namespace
                if namespace not in relations_by_namespace:
                    relations_by_namespace[namespace] = []
                relations_by_namespace[namespace].append(relation)

            # Process each namespace group in batches to avoid overwhelming the database
            BULK_BATCH_SIZE = 100  # Max relations per bulk request

            for namespace, relations in relations_by_namespace.items():
                logger.info(
                    f"Creating {len(relations)} relations in namespace '{namespace}' using bulk API"
                )

                # Process relations in batches
                for batch_start in range(0, len(relations), BULK_BATCH_SIZE):
                    batch_end = min(batch_start + BULK_BATCH_SIZE, len(relations))
                    batch = relations[batch_start:batch_end]

                    if len(relations) > BULK_BATCH_SIZE:
                        logger.info(
                            f"Processing batch {batch_start//BULK_BATCH_SIZE + 1}: "
                            f"relations {batch_start+1} to {batch_end} of {len(relations)}"
                        )

                    # Log individual relations for visibility
                    for relation in batch:
                        relation_desc = f"{relation.source.kind}/{relation.source.name} --{relation.relation}--> {relation.target.kind}/{relation.target.name}"
                        if relation.relation == "IS_A":
                            logger.info(f"Queued IS_A relation: {relation_desc}")
                        else:
                            logger.debug(f"Queued relation: {relation_desc}")

                    # Create bulk request for this batch
                    bulk_request = BulkEntityRelationCreateRequest(
                        relations=batch, namespace=namespace
                    )

                    try:
                        resp = create_entity_relations_bulk.sync_detailed(
                            client=api_client,
                            body=bulk_request,
                        )

                        if resp.status_code == 201 and resp.parsed:
                            bulk_response = resp.parsed
                            logger.info(
                                f"Bulk relation creation completed for batch in namespace '{namespace}':"
                            )
                            logger.info(
                                f"  - Total requested: {bulk_response.total_requested}"
                            )
                            logger.info(
                                f"  - Successfully created: {bulk_response.success_count}"
                            )
                            logger.info(f"  - Failed: {bulk_response.failure_count}")

                            # Log failed relations with details
                            if (
                                bulk_response.failure_count > 0
                                and bulk_response.failed_relations
                            ):
                                logger.warning(
                                    f"Failed to create {bulk_response.failure_count} relations:"
                                )
                                for failed_relation in bulk_response.failed_relations:
                                    logger.error(
                                        f"  - Failed relation: {failed_relation.error}"
                                    )

                            # Log successful IS_A relations for visibility
                            if bulk_response.created_relations:
                                for created_relation in bulk_response.created_relations:
                                    if created_relation.relation == "IS_A":
                                        relation_desc = f"{created_relation.source.kind}/{created_relation.source.name} --{created_relation.relation}--> {created_relation.target.kind}/{created_relation.target.name}"
                                        logger.info(
                                            f"Successfully created IS_A relation: {relation_desc}"
                                        )
                        else:
                            logger.error(
                                f"Failed to create bulk relations batch for namespace '{namespace}': {resp.status_code}"
                            )
                            log_client_error(resp)

                            # Fall back to individual creation for this batch
                            logger.info(
                                "Falling back to individual relation creation for batch"
                            )
                            for relation in batch:
                                relation_desc = f"{relation.source.kind}/{relation.source.name} --{relation.relation}--> {relation.target.kind}/{relation.target.name}"

                                if relation.relation == "IS_A":
                                    logger.info(
                                        f"Creating IS_A relation (fallback): {relation_desc}"
                                    )
                                else:
                                    logger.debug(
                                        f"Creating relation (fallback): {relation_desc}"
                                    )

                                individual_resp = create_entity_relation.sync_detailed(
                                    client=api_client,
                                    namespace=relation.namespace,
                                    body=relation,
                                )
                                if individual_resp.status_code != 201:
                                    if relation.relation == "IS_A":
                                        logger.error(
                                            f"Failed to create IS_A relation (fallback): {relation_desc} - Status: {individual_resp.status_code}"
                                        )
                                    log_client_error(individual_resp)
                                else:
                                    if relation.relation == "IS_A":
                                        logger.info(
                                            f"Successfully created IS_A relation (fallback): {relation_desc}"
                                        )
                                    else:
                                        logger.debug(
                                            "Relation created successfully (fallback)"
                                        )

                    except Exception as e:
                        logger.error(
                            f"Error creating bulk relations batch for namespace '{namespace}': {e}"
                        )
                        # Fall back to individual creation for this batch
                        logger.info(
                            "Falling back to individual relation creation for batch (exception)"
                        )
                        for relation in batch:
                            relation_desc = f"{relation.source.kind}/{relation.source.name} --{relation.relation}--> {relation.target.kind}/{relation.target.name}"

                            try:
                                if relation.relation == "IS_A":
                                    logger.info(
                                        f"Creating IS_A relation (fallback): {relation_desc}"
                                    )
                                else:
                                    logger.debug(
                                        f"Creating relation (fallback): {relation_desc}"
                                    )

                                individual_resp = create_entity_relation.sync_detailed(
                                    client=api_client,
                                    namespace=relation.namespace,
                                    body=relation,
                                )
                                if individual_resp.status_code != 201:
                                    if relation.relation == "IS_A":
                                        logger.error(
                                            f"Failed to create IS_A relation (fallback): {relation_desc} - Status: {individual_resp.status_code}"
                                        )
                                    log_client_error(individual_resp)
                                else:
                                    if relation.relation == "IS_A":
                                        logger.info(
                                            f"Successfully created IS_A relation (fallback): {relation_desc}"
                                        )
                                    else:
                                        logger.debug(
                                            "Relation created successfully (fallback)"
                                        )
                            except Exception as individual_e:
                                logger.error(
                                    f"Error creating individual relation {relation_desc}: {individual_e}"
                                )
        else:
            logger.debug("No relations to create")

    return wrapped


class DiscoveryProcessor:
    def __init__(self, config: Config, provider_names: list[str] = None):
        self.config = config.discovery
        self.ext_mgr = DiscoveryExtensionManager()

        # Log config with sensitive fields masked
        discovery_config_masked = config.discovery.model_dump_masked()
        logger.info(
            f"Initialized DiscoveryProcessor with config: {discovery_config_masked}"
        )

        self._client = AuthenticatedClient(
            base_url=config.discovery.api_base_url,
            token=config.discovery.opaque_token,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Devgraph-Environment": str(config.discovery.environment) or "",
            },
        )
        self.environment = str(config.discovery.environment) or ""
        self.providers = self._hydrate_providers(provider_names)

    def _fetch_providers_from_api(self) -> list[dict]:
        """Fetch provider configurations from API with decrypted secrets.

        Returns:
            List of provider config dicts from API
        """
        try:
            url = f"{self.config.api_base_url}/api/v1/discovery/admin/configured-providers"
            headers = {
                "Authorization": f"Bearer {self.config.opaque_token}",
                "Devgraph-Environment": str(self.environment),
            }

            logger.info(f"Fetching provider configs from API: {url}")
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                providers = data.get("providers", [])
                logger.info(f"Fetched {len(providers)} provider configs from API")
                return providers
            else:
                logger.error(
                    f"Failed to fetch providers from API: {response.status_code} - {response.text}"
                )
                return []

        except Exception as e:
            logger.error(f"Error fetching providers from API: {e}")
            return []

    def _hydrate_providers(self, provider_names: list[str] = None) -> list[Provider]:
        """Hydrate providers from configured molecules.

        Args:
            provider_names: Optional list of provider names to filter

        Returns:
            List of hydrated Provider instances
        """
        logger.debug("Hydrating discovery providers from configured molecules")

        # Get molecule configs from configuration
        provider_configs = self.config.molecules

        # Hydrate provider instances
        providers = []
        for provider_config in provider_configs:
            logger.info(
                f"Processing provider config: {provider_config.model_dump_masked()}"
            )
            if provider_names and provider_config.name not in provider_names:
                logger.info(
                    f"Skipping provider {provider_config.type} as it is not in the specified provider names"
                )
                continue

            try:
                molecule_cls = self.ext_mgr.provider(provider_config.type)
                if molecule_cls is None:
                    logger.error(f"No molecule found for type {provider_config.type}")
                    continue
                provider_cls = molecule_cls.get_discovery_provider()
                if provider_cls is None:
                    logger.error(
                        f"Molecule {provider_config.type} has no discovery provider"
                    )
                    continue
                provider = provider_cls.from_config(provider_config)
                providers.append(provider)
            except Exception as e:
                logger.error(f"Failed to hydrate provider {provider_config.name}: {e}")
                continue

        logger.debug(f"Scheduled providers: {', '.join([p.name for p in providers])}")
        return providers

    def reload_providers_from_api(self):
        """Reload provider configurations from API and update running providers.

        This method is called periodically when source=api to pick up config changes.
        """
        logger.info("Reloading provider configurations from API")

        try:
            # Fetch fresh provider configs
            new_providers = self._hydrate_providers()

            # Check if providers changed
            old_names = {p.name for p in self.providers}
            new_names = {p.name for p in new_providers}

            added = new_names - old_names
            removed = old_names - new_names

            if added or removed:
                logger.info(
                    f"Provider configuration changed - Added: {added}, Removed: {removed}"
                )

                # Clear existing scheduled jobs for removed providers
                schedule.clear()

                # Update providers list
                self.providers = new_providers

                # Reschedule all providers
                for provider in self.providers:
                    logger.info(f"Rescheduling provider: {provider.name}")
                    schedule.every(provider.every).seconds.do(
                        run_threaded,
                        run_provider(provider, self._client, self.environment),
                    )

                logger.info(f"Successfully reloaded {len(new_providers)} providers")
            else:
                logger.debug("No provider configuration changes detected")

        except Exception as e:
            logger.error(f"Failed to reload providers from API: {e}")

    def create_entity_definitions(self):
        """Create entity definitions for all providers.

        This method attempts to create entity definitions but does not fail if the API
        is unreachable. Entity definitions will be created on the first successful
        discovery run if they don't exist yet.
        """
        try:
            for provider in self.providers:
                logger.info(f"Creating entity definition for provider: {provider.name}")
                for entity_definition in provider.entity_definitions():
                    logger.debug(f"Creating entity definition: {entity_definition}")
                    # Convert to API model
                    api_spec = EntityDefinitionSpec.from_dict(entity_definition.to_dict())
                    detailed_response = create_entity_definition.sync_detailed(
                        client=self._client,
                        body=api_spec,
                    )
                    if detailed_response.status_code == 201:
                        logger.debug("Entity definition created successfully")
                    elif detailed_response.status_code == 409:
                        logger.debug("Entity definition already exists, skipping")
                    else:
                        log_client_error(detailed_response)
        except Exception as e:
            logger.warning(
                f"Failed to create entity definitions at startup: {e}. "
                "This is not fatal - definitions will be created during discovery if needed."
            )

    def create_all_entity_definitions(self):
        """Create all entity definitions from the registry, not just from providers.

        This method auto-discovers all available entity definitions and creates them,
        allowing schema setup independent of provider instances.
        """
        logger.info("Auto-discovering and creating all entity definitions")

        # Auto-discover all entity definitions
        discovered_count = auto_discover_all_definitions()
        logger.info(f"Discovered {discovered_count} entity definitions")

        # Create all definitions via the registry
        create_all_definitions(self._client)

    def discover(self, oneshot: bool = False):
        for i, provider in enumerate(self.providers):
            if not oneshot:
                logger.info(f"Scheduling provider: {provider}")
                # Schedule for recurring execution
                schedule.every(provider.every).seconds.do(
                    run_threaded, run_provider(provider, self._client, self.environment)
                )
                # Run immediately in background with splay to avoid thundering herd
                splay = i * 2  # 0s, 2s, 4s, 6s...

                def run_with_delay(prov, delay):
                    time.sleep(delay)
                    logger.info(f"Running initial discovery for provider: {prov.name}")
                    run_provider(prov, self._client, self.environment)()

                logger.info(
                    f"Scheduling initial run with {splay}s delay: {provider.name}"
                )
                thread = threading.Thread(
                    target=run_with_delay, args=(provider, splay), daemon=True
                )
                thread.start()
            else:
                logger.info(f"Running oneshot provider: {provider}")
                run_provider(provider, self._client, self.environment)()

        if not oneshot:
            logger.info("Starting discovery loop")
            while True:
                schedule.run_pending()
                time.sleep(1)
