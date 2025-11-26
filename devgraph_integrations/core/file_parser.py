"""Utility functions for parsing entity files from various sources.

This module provides reusable functions for parsing entity definitions from file content,
supporting YAML and JSON formats. It can be used by any provider that reads files from
different transports (GitHub API, HTTP, file system, etc.).
"""

import json
from typing import Any, Dict, List, Optional, Tuple

import yaml  # type: ignore
from loguru import logger

from devgraph_integrations.types.entities import (
    Entity,
    EntityMetadata,
    EntityReference,
    EntityRelation,
)


def parse_entity_file(
    content: str,
    source_name: str,
    file_path: str,
    namespace: str = "default",
    additional_labels: Optional[Dict[str, str]] = None,
) -> Tuple[List[Entity], List[EntityRelation]]:
    """Parse entity definitions and relationships from file content.

    Args:
        content: File content as string
        source_name: Name of the source (e.g., repository name, URL)
        file_path: Path of the file within the source
        namespace: Default namespace for entities without one specified
        additional_labels: Additional labels to add to all parsed entities

    Returns:
        Tuple of (entities, relations) parsed from the file

    Examples:
        >>> content = '''
        ... entities:
        ...   - apiVersion: v1
        ...     kind: Component
        ...     metadata:
        ...       name: my-service
        ...     spec:
        ...       type: service
        ... relations:
        ...   - relation: dependsOn
        ...     source: {apiVersion: v1, kind: Component, name: my-service, namespace: default}
        ...     target: {apiVersion: v1, kind: Database, name: my-db, namespace: default}
        ... '''
        >>> entities, relations = parse_entity_file(content, "my-repo", ".devgraph.yaml")
        >>> len(entities), len(relations)
        (1, 1)
    """
    entities = []
    relations = []
    additional_labels = additional_labels or {}

    try:
        # Validate file content first
        is_valid, validation_errors = validate_entity_file_content(
            content, source_name, file_path
        )
        if not is_valid:
            logger.error(f"Validation failed for {source_name}:{file_path}")
            for error in validation_errors:
                logger.error(f"  - {error}")
            return entities, relations

        # Try YAML first, then JSON
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError:
            data = json.loads(content)

        if not data:
            logger.debug(f"No data found in {source_name}:{file_path}")
            return entities, relations

        # Handle different file formats
        entities_data, relations_data = _extract_entities_and_relations_from_data(
            data, source_name, file_path
        )

        # Parse entities
        for entity_data in entities_data:
            entity = _create_entity_from_data(
                entity_data, source_name, file_path, namespace, additional_labels
            )
            if entity:
                entities.append(entity)

        # Parse relations
        for relation_data in relations_data:
            relation = _create_relation_from_data(
                relation_data, source_name, file_path, namespace
            )
            if relation:
                relations.append(relation)

    except Exception as e:
        logger.error(
            f"Error parsing entities/relations from {source_name}:{file_path}: {e}"
        )

    logger.info(
        f"Parsed {len(entities)} entities and {len(relations)} relations from {source_name}:{file_path}"
    )
    return entities, relations


def _extract_entities_and_relations_from_data(
    data: Any, source_name: str, file_path: str
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Extract entity and relation data from parsed file content.

    Supports multiple formats:
    - Single entity (dict with apiVersion/kind)
    - List of entities
    - Wrapper object with 'entities' and/or 'relations' keys
    """
    entities_data = []
    relations_data = []

    if isinstance(data, dict):
        # Single entity
        if "apiVersion" in data and "kind" in data:
            entities_data = [data]
        # Wrapper with entities/relations keys
        else:
            if "entities" in data:
                entities_list = data["entities"]
                if isinstance(entities_list, list):
                    entities_data = entities_list
                else:
                    logger.warning(
                        f"'entities' key contains non-list in {source_name}:{file_path}"
                    )

            if "relations" in data:
                relations_list = data["relations"]
                if isinstance(relations_list, list):
                    relations_data = relations_list
                else:
                    logger.warning(
                        f"'relations' key contains non-list in {source_name}:{file_path}"
                    )

            # If no explicit entities/relations keys, check if it's just entities
            if not entities_data and not relations_data:
                logger.warning(
                    f"No entities or relations found in {source_name}:{file_path}"
                )

    elif isinstance(data, list):
        # List of entities (legacy format)
        entities_data = data
    else:
        logger.warning(f"Unexpected data structure in {source_name}:{file_path}")

    return entities_data, relations_data


def _create_entity_from_data(
    entity_data: Dict[str, Any],
    source_name: str,
    file_path: str,
    namespace: str,
    additional_labels: Dict[str, str],
) -> Optional[Entity]:
    """Create an Entity object from parsed data."""
    if not isinstance(entity_data, dict):
        logger.warning(f"Invalid entity data type in {source_name}:{file_path}")
        return None

    if "apiVersion" not in entity_data or "kind" not in entity_data:
        logger.warning(
            f"Invalid entity format (missing apiVersion/kind) in {source_name}:{file_path}"
        )
        return None

    try:
        # Validate required fields
        if not isinstance(entity_data.get("apiVersion"), str):
            logger.error(f"Invalid or missing apiVersion in {source_name}:{file_path}")
            return None

        if not isinstance(entity_data.get("kind"), str):
            logger.error(f"Invalid or missing kind in {source_name}:{file_path}")
            return None

        # Process metadata
        metadata = entity_data.get("metadata", {})
        if not isinstance(metadata, dict):
            logger.error(
                f"Invalid metadata (must be dict) in {source_name}:{file_path}"
            )
            return None

        # Validate required metadata fields
        if "name" not in metadata:
            logger.error(f"Missing required metadata.name in {source_name}:{file_path}")
            return None

        if not isinstance(metadata["name"], str) or not metadata["name"].strip():
            logger.error(
                f"Invalid metadata.name (must be non-empty string) in {source_name}:{file_path}"
            )
            return None

        if "namespace" not in metadata:
            metadata["namespace"] = namespace
        if "labels" not in metadata:
            metadata["labels"] = {}

        # Validate namespace
        if (
            not isinstance(metadata["namespace"], str)
            or not metadata["namespace"].strip()
        ):
            logger.error(f"Invalid metadata.namespace in {source_name}:{file_path}")
            return None

        # Add source tracking labels
        metadata["labels"]["source-name"] = source_name
        metadata["labels"]["source-file"] = file_path

        # Add any additional labels
        metadata["labels"].update(additional_labels)

        # Validate spec
        spec = entity_data.get("spec", {})
        if spec is not None and not isinstance(spec, dict):
            logger.error(
                f"Invalid spec (must be dict or null) in {source_name}:{file_path}"
            )
            return None

        # Create and validate entity
        entity = Entity(
            apiVersion=entity_data["apiVersion"],
            kind=entity_data["kind"],
            metadata=EntityMetadata(**metadata),
            spec=spec,
        )

        # Additional validation: ensure entity can generate a valid ID
        try:
            entity_id = entity.id
            if not entity_id or not isinstance(entity_id, str):
                logger.error(
                    f"Entity generates invalid ID in {source_name}:{file_path}"
                )
                return None
        except Exception as id_error:
            logger.error(
                f"Error generating entity ID in {source_name}:{file_path}: {id_error}"
            )
            return None

        logger.debug(
            f"Created entity {entity.kind}:{entity.metadata.name} from {source_name}:{file_path}"
        )
        return entity

    except Exception as e:
        logger.error(f"Error creating entity from {source_name}:{file_path}: {e}")
        logger.debug(f"Entity data: {entity_data}")
        return None


def _create_relation_from_data(
    relation_data: Dict[str, Any], source_name: str, file_path: str, namespace: str
) -> Optional[EntityRelation]:
    """Create an EntityRelation object from parsed data."""
    if not isinstance(relation_data, dict):
        logger.warning(f"Invalid relation data type in {source_name}:{file_path}")
        return None

    if (
        "relation" not in relation_data
        or "source" not in relation_data
        or "target" not in relation_data
    ):
        logger.warning(
            f"Invalid relation format (missing relation/source/target) in {source_name}:{file_path}"
        )
        return None

    try:
        # Parse source reference
        source_ref_data = relation_data["source"]
        if "namespace" not in source_ref_data:
            source_ref_data["namespace"] = namespace
        source_ref = EntityReference(**source_ref_data)

        # Parse target reference
        target_ref_data = relation_data["target"]
        if "namespace" not in target_ref_data:
            target_ref_data["namespace"] = namespace
        target_ref = EntityReference(**target_ref_data)

        # Extract or create metadata
        from devgraph_integrations.types.entities import RelationMetadata

        metadata_data = relation_data.get("metadata", {})
        labels = metadata_data.get("labels", {})
        annotations = metadata_data.get("annotations", {})

        # Add source tracking labels (like entities do)
        labels["source-name"] = source_name
        labels["source-file"] = file_path
        labels["source-type"] = "declared"  # Relations from .devgraph.yaml are declared
        labels["managed-by"] = f"file:{source_name}"  # Managed by the file provider

        metadata = RelationMetadata(labels=labels, annotations=annotations)

        # Extract spec if provided
        spec = relation_data.get("spec", {})

        # Create relation with metadata and spec
        relation = EntityRelation(
            namespace=relation_data.get("namespace", namespace),
            relation=relation_data["relation"],
            source=source_ref,
            target=target_ref,
            metadata=metadata,
            spec=spec,
        )

        logger.debug(
            f"Created relation {relation.relation}: {source_ref.name} -> {target_ref.name} from {source_name}:{file_path}"
        )
        return relation

    except Exception as e:
        logger.error(f"Error creating relation from {source_name}:{file_path}: {e}")
        return None


def validate_entity_file_format(content: str) -> bool:
    """Validate if file content contains valid entity definitions.

    Args:
        content: File content as string

    Returns:
        True if content appears to contain valid entity definitions
    """
    try:
        # Try parsing as YAML/JSON
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError:
            data = json.loads(content)

        if not data:
            return False

        # Check if it contains entity-like structure
        entities_data, relations_data = _extract_entities_and_relations_from_data(
            data, "validation", "test"
        )
        return len(entities_data) > 0 or len(relations_data) > 0

    except Exception:
        return False


def validate_entity_file_content(
    content: str, source_name: str = "unknown", file_path: str = "unknown"
) -> Tuple[bool, List[str]]:
    """Thoroughly validate entity file content and return detailed errors.

    Args:
        content: File content as string
        source_name: Name of the source for error reporting
        file_path: Path of the file for error reporting

    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    errors = []

    try:
        # Parse file content
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                errors.append(f"Invalid YAML/JSON format: {e}")
                return False, errors

        if not data:
            errors.append("File contains no data")
            return False, errors

        # Extract entities and relations
        entities_data, relations_data = _extract_entities_and_relations_from_data(
            data, source_name, file_path
        )

        if not entities_data and not relations_data:
            errors.append("No entities or relations found in file")
            return False, errors

        # Validate each entity
        for i, entity_data in enumerate(entities_data):
            entity_errors = _validate_entity_data(entity_data, f"entity[{i}]")
            errors.extend(entity_errors)

        # Validate each relation
        for i, relation_data in enumerate(relations_data):
            relation_errors = _validate_relation_data(relation_data, f"relation[{i}]")
            errors.extend(relation_errors)

        return len(errors) == 0, errors

    except Exception as e:
        errors.append(f"Unexpected error during validation: {e}")
        return False, errors


def _validate_entity_data(entity_data: Any, context: str) -> List[str]:
    """Validate entity data structure and return errors."""
    errors = []

    if not isinstance(entity_data, dict):
        errors.append(f"{context}: Entity must be a dictionary")
        return errors

    # Check required fields
    if "apiVersion" not in entity_data:
        errors.append(f"{context}: Missing required field 'apiVersion'")
    elif not isinstance(entity_data["apiVersion"], str):
        errors.append(f"{context}: 'apiVersion' must be a string")
    elif not entity_data["apiVersion"].strip():
        errors.append(f"{context}: 'apiVersion' cannot be empty")

    if "kind" not in entity_data:
        errors.append(f"{context}: Missing required field 'kind'")
    elif not isinstance(entity_data["kind"], str):
        errors.append(f"{context}: 'kind' must be a string")
    elif not entity_data["kind"].strip():
        errors.append(f"{context}: 'kind' cannot be empty")

    # Check metadata
    metadata = entity_data.get("metadata")
    if metadata is None:
        errors.append(f"{context}: Missing required field 'metadata'")
    elif not isinstance(metadata, dict):
        errors.append(f"{context}: 'metadata' must be a dictionary")
    else:
        # Check metadata.name
        if "name" not in metadata:
            errors.append(f"{context}: Missing required field 'metadata.name'")
        elif not isinstance(metadata["name"], str):
            errors.append(f"{context}: 'metadata.name' must be a string")
        elif not metadata["name"].strip():
            errors.append(f"{context}: 'metadata.name' cannot be empty")

        # Check metadata.namespace if present
        if "namespace" in metadata:
            if not isinstance(metadata["namespace"], str):
                errors.append(f"{context}: 'metadata.namespace' must be a string")
            elif not metadata["namespace"].strip():
                errors.append(f"{context}: 'metadata.namespace' cannot be empty")

    # Check spec if present
    if "spec" in entity_data:
        spec = entity_data["spec"]
        if spec is not None and not isinstance(spec, dict):
            errors.append(f"{context}: 'spec' must be a dictionary or null")

    return errors


def _validate_relation_data(relation_data: Any, context: str) -> List[str]:
    """Validate relation data structure and return errors."""
    errors = []

    if not isinstance(relation_data, dict):
        errors.append(f"{context}: Relation must be a dictionary")
        return errors

    # Check required fields
    required_fields = ["relation", "source", "target"]
    for field in required_fields:
        if field not in relation_data:
            errors.append(f"{context}: Missing required field '{field}'")
        elif field == "relation":
            if not isinstance(relation_data[field], str):
                errors.append(f"{context}: '{field}' must be a string")
            elif not relation_data[field].strip():
                errors.append(f"{context}: '{field}' cannot be empty")
        else:  # source or target
            if not isinstance(relation_data[field], dict):
                errors.append(f"{context}: '{field}' must be a dictionary")
            else:
                # Validate entity reference
                ref_errors = _validate_entity_reference(
                    relation_data[field], f"{context}.{field}"
                )
                errors.extend(ref_errors)

    # Check optional spec field
    if "spec" in relation_data:
        spec = relation_data["spec"]
        if spec is not None and not isinstance(spec, dict):
            errors.append(f"{context}: 'spec' must be a dictionary or null")

    return errors


def _validate_entity_reference(ref_data: dict, context: str) -> List[str]:
    """Validate entity reference data structure."""
    errors = []

    required_fields = ["apiVersion", "kind", "name"]
    for field in required_fields:
        if field not in ref_data:
            errors.append(f"{context}: Missing required field '{field}'")
        elif not isinstance(ref_data[field], str):
            errors.append(f"{context}: '{field}' must be a string")
        elif not ref_data[field].strip():
            errors.append(f"{context}: '{field}' cannot be empty")

    # namespace is optional but if present must be valid
    if "namespace" in ref_data:
        if not isinstance(ref_data["namespace"], str):
            errors.append(f"{context}: 'namespace' must be a string")
        elif not ref_data["namespace"].strip():
            errors.append(f"{context}: 'namespace' cannot be empty")

    return errors
