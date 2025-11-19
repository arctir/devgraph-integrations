from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from devgraph_client.client import (
    AuthenticatedClient,
)
from loguru import logger

from devgraph_integrations.core.entity import EntityDefinitionSpec

from .state import GraphMutations

if TYPE_CHECKING:
    from .versioning import ProviderVersionSupport


class Provider(ABC):
    """Base class for all discovery providers.

    Providers should define VERSION_SUPPORT to enable config versioning and migrations.
    """

    # Subclasses should define their version support
    VERSION_SUPPORT: Optional["ProviderVersionSupport"] = None

    def __init__(self, name: str, every: int) -> None:
        self.name = name
        self.every = every

    @property
    def namespace(self) -> str:
        """
        Get the namespace for this provider's entities.
        Providers should override this or ensure their config has a namespace.
        """
        if hasattr(self, "config") and hasattr(self.config, "namespace"):
            return self.config.namespace
        return "default"

    @abstractmethod
    def entity_definitions(self) -> list[EntityDefinitionSpec]:
        """
        Return a list of entity definitions that this provider can create.
        This method should return a list of EntityDefinitionSpec instances.
        If the provider does not support entity definitions, it can return an empty list.
        """
        pass

    @abstractmethod
    def reconcile(self, client: AuthenticatedClient) -> GraphMutations:
        """
        Reconcile the state of the provider with the current state of the graph.
        This method should return a set of mutations to apply to the graph.
        """
        pass

    @classmethod
    def load_config(cls, raw_config: dict, config_version: int = 1) -> dict:
        """Load and migrate config if needed.

        Args:
            raw_config: The raw config dictionary from the database
            config_version: The config schema version

        Returns:
            The migrated config dictionary ready for validation

        Raises:
            ValueError: If the config version is not supported
        """
        if cls.VERSION_SUPPORT is None:
            # Provider doesn't use versioning, return config as-is
            return raw_config

        # Check if version is supported
        if not cls.VERSION_SUPPORT.is_supported(config_version):
            raise ValueError(
                f"Config version {config_version} is no longer supported by {cls.__name__}. "
                f"Current version: {cls.VERSION_SUPPORT.current_version}"
            )

        # Warn about deprecation
        warning = cls.VERSION_SUPPORT.get_deprecation_warning(config_version)
        if warning:
            logger.warning(f"{cls.__name__}: {warning}")

        # Migrate config to current version if needed
        if config_version < cls.VERSION_SUPPORT.current_version:
            logger.info(
                f"Migrating {cls.__name__} config from v{config_version} to "
                f"v{cls.VERSION_SUPPORT.current_version}"
            )
            return cls.VERSION_SUPPORT.migrate_config(raw_config, config_version)

        return raw_config

    @classmethod
    def from_config(
        cls,
        provider_config: dict,
        config_version: int = 1,
    ) -> "Provider":
        """Create a provider instance from config.

        Args:
            provider_config: Provider configuration dict with 'name', 'every', 'config'
            config_version: Schema version of the config (default: 1)

        Returns:
            Initialized provider instance
        """
        # Load and migrate config if needed
        migrated_config = cls.load_config(provider_config.config, config_version)

        # Validate with Pydantic model
        c = cls._config_cls.model_validate(migrated_config)

        return cls(provider_config.name, provider_config.every, c)


class DefinitionOnlyProvider(Provider):
    """Base class for providers that only provide entity definitions.

    This provider type does not participate in entity reconciliation
    and should only be used for providing static entity definitions.
    """

    def reconcile(self, client: AuthenticatedClient) -> GraphMutations:
        """Definition-only providers don't create runtime entities.

        Returns:
            Empty mutations since this provider only provides definitions
        """
        from loguru import logger

        logger.debug(
            f"Definition-only provider '{self.name}' - skipping reconciliation"
        )

        return GraphMutations(
            create_entities=[],
            delete_entities=[],
            create_relations=[],
            delete_relations=[],
        )
