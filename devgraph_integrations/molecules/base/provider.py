"""Base provider classes for molecule implementations.

This module provides base classes that implement common patterns across
molecule providers to reduce code duplication and ensure consistency.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from loguru import logger

from devgraph_client.client import AuthenticatedClient
from devgraph_integrations.core.provider import Provider
from devgraph_integrations.core.state import GraphMutations
from devgraph_integrations.types.entities import Entity, EntityMetadata

from .config import MoleculeProviderConfig


class MoleculeProvider(Provider, ABC):
    """Base class for molecule providers.

    Provides common functionality for molecule providers including:
    - Consistent initialization patterns
    - Standard error handling in reconciliation
    - Helper methods for entity and relation creation
    - Logging patterns

    Attributes:
        _config_cls: Configuration class for this provider (must be overridden)
        config: Provider configuration instance
        client: Provider-specific client instance (if applicable)
    """

    # Must be overridden by subclasses
    _config_cls: Type[MoleculeProviderConfig] = None
    _display_name: str = None  # Human-readable name (e.g., "GitHub")
    _description: str = None  # Description of what this molecule does
    _logo: str = None  # Logo as inline SVG string or URL (http://, https://, or data:)

    def __init__(self, name: str, every: int, config: MoleculeProviderConfig) -> None:
        """Initialize molecule provider.

        Args:
            name: Unique name for this provider instance
            every: Interval in seconds for reconciliation runs
            config: Provider configuration instance
        """
        super().__init__(name, every)
        self.config = config
        self.client = self._init_client(config) if self._should_init_client() else None

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get JSON schema for provider configuration.

        Returns:
            JSON schema dict describing the configuration structure
        """
        if cls._config_cls is None:
            raise ValueError(f"{cls.__name__} must define _config_cls")
        return cls._config_cls.model_json_schema()

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get provider metadata including display name, description, and logo.

        Returns:
            Dict containing provider metadata
        """
        metadata = {
            "type": cls.__name__.replace("Provider", "").lower(),
            "display_name": cls._display_name or cls.__name__.replace("Provider", ""),
            "description": cls._description or cls.__doc__.split("\n")[0]
            if cls.__doc__
            else "",
            "config_schema": cls.get_config_schema(),
        }

        # Only include logo if it's set (can be SVG string, URL, or data URI)
        if cls._logo:
            metadata["logo"] = cls._logo

        return metadata

    def _should_init_client(self) -> bool:
        """Whether this provider should initialize a client.

        Override this method to return False for providers that don't need clients.

        Returns:
            True if client should be initialized, False otherwise
        """
        return True

    def _init_client(self, config: MoleculeProviderConfig) -> Any:
        """Initialize provider-specific client.

        Override this method to create and configure the client for your provider.

        Args:
            config: Provider configuration

        Returns:
            Initialized client instance
        """
        return None

    def reconcile(self, client: AuthenticatedClient) -> GraphMutations:
        """Reconcile entities with the current graph state.

        Provides standard error handling and logging around provider-specific
        reconciliation logic.

        Args:
            client: Authenticated Devgraph API client

        Returns:
            GraphMutations containing entities and relations to create/delete.
            Returns empty mutations if reconciliation fails to prevent partial state.
        """
        provider_name = self.__class__.__name__
        logger.debug(f"Reconciling entities for {provider_name}")

        try:
            mutations = self._reconcile_entities(client)
            logger.info(
                f"{provider_name} reconciliation completed: "
                f"{len(mutations.create_entities)} entities, "
                f"{len(mutations.create_relations)} relations to create"
            )
            return mutations
        except Exception as e:
            logger.error(f"Failed to reconcile {provider_name} entities: {e}")
            logger.exception("Reconciliation error details:")
            return self._get_empty_mutations()

    @abstractmethod
    def _reconcile_entities(self, client: AuthenticatedClient) -> GraphMutations:
        """Perform provider-specific entity reconciliation.

        Override this method with your provider's reconciliation logic.

        Args:
            client: Authenticated Devgraph API client

        Returns:
            GraphMutations containing entities and relations to create/delete
        """
        pass

    def _get_empty_mutations(self) -> GraphMutations:
        """Get empty mutations object.

        Returns:
            Empty GraphMutations instance
        """
        return GraphMutations(
            create_entities=[],
            delete_entities=[],
            create_relations=[],
            delete_relations=[],
        )

    def _create_mutations(
        self,
        create_entities: List[Entity] = None,
        delete_entities: List[Entity] = None,
        create_relations: List[Any] = None,
        delete_relations: List[Any] = None,
    ) -> GraphMutations:
        """Create GraphMutations object with provided lists.

        Args:
            create_entities: Entities to create
            delete_entities: Entities to delete
            create_relations: Relations to create
            delete_relations: Relations to delete

        Returns:
            GraphMutations object with provided lists
        """
        return GraphMutations(
            create_entities=create_entities or [],
            delete_entities=delete_entities or [],
            create_relations=create_relations or [],
            delete_relations=delete_relations or [],
        )

    def _create_entity(
        self,
        entity_class: Type[Entity],
        name: str,
        spec: Any,
        labels: Optional[Dict[str, str]] = None,
    ) -> Entity:
        """Create entity with standard metadata structure.

        Args:
            entity_class: Entity class to instantiate
            name: Entity name
            spec: Entity specification
            labels: Optional labels for entity metadata

        Returns:
            Created entity instance
        """
        return entity_class(
            metadata=EntityMetadata(
                name=name,
                namespace=self.config.namespace,
                labels=labels or {},
            ),
            spec=spec,
        )

    def _create_repository_relation(
        self,
        relation_class: Type[Any],
        source_reference: Any,
        repo_url: str,
    ) -> Any:
        """Create field-selected relation to GitHub repository.

        Helper method for creating relations between entities and GitHub repositories
        based on repository URL matching.

        Args:
            relation_class: Relation class to instantiate
            source_reference: Source entity reference
            repo_url: Repository URL to match

        Returns:
            Created relation instance
        """
        return relation_class.with_target_selector(
            relation="USES",
            source=source_reference,
            target_selector=f"spec.url={repo_url}",
            namespace=self.config.namespace,
            properties={"repo_url": repo_url},
            target_api_version="entities.devgraph.ai/v1",
            target_kind="GitHubRepository",
        )

    def _safe_entity_creation(
        self,
        entity_factory: callable,
        entity_data: Dict[str, Any],
        entity_type: str = "entity",
    ) -> Optional[Entity]:
        """Safely create entity with error handling.

        Args:
            entity_factory: Function that creates the entity
            entity_data: Data used to create the entity
            entity_type: Type name for logging purposes

        Returns:
            Created entity or None if creation failed
        """
        try:
            return entity_factory()
        except Exception as e:
            entity_id = entity_data.get("id") or entity_data.get("name") or "unknown"
            logger.warning(f"Failed to create {entity_type} '{entity_id}': {e}")
            return None

    def _process_with_error_handling(
        self,
        items: List[Any],
        processor: callable,
        item_type: str = "item",
    ) -> List[Any]:
        """Process list of items with individual error handling.

        Args:
            items: List of items to process
            processor: Function to process each item
            item_type: Type name for logging purposes

        Returns:
            List of successfully processed results
        """
        results = []
        for item in items:
            try:
                result = processor(item)
                if result is not None:
                    results.append(result)
            except Exception as e:
                item_id = getattr(item, "id", getattr(item, "name", "unknown"))
                logger.warning(f"Failed to process {item_type} '{item_id}': {e}")
                continue

        return results


class HttpApiMoleculeProvider(MoleculeProvider):
    """Base class for HTTP API-based molecule providers.

    Extends MoleculeProvider with common patterns for providers that
    interact with HTTP APIs.
    """

    def _should_init_client(self) -> bool:
        """HTTP API providers should initialize clients."""
        return True

    def _get_client_class(self):
        """Get the client class for this provider.

        Override this method to specify the client class.

        Returns:
            Client class to instantiate
        """
        from .client import RestApiClient

        return RestApiClient

    def _init_client(self, config: MoleculeProviderConfig) -> Any:
        """Initialize HTTP API client.

        Args:
            config: Provider configuration

        Returns:
            Initialized HTTP API client
        """
        client_class = self._get_client_class()
        return client_class(
            base_url=config.api_url,
            token=config.token,
            timeout=getattr(config, "timeout", 30),
        )
