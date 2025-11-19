"""Configuration source extension system.

This module provides a pluggable system for loading configuration from different sources.
The default configuration source is file-based, but additional configuration sources
can be added via stevedore plugins.

Example plugin registration in pyproject.toml:

    [tool.poetry.plugins."devgraph_integrations.config.sources"]
    "api" = "my_package.config:APIConfigSource"
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
from stevedore import ExtensionManager  # type: ignore


class ConfigSource(ABC):
    """Base class for configuration sources.

    Configuration sources are responsible for loading configuration data
    from various backends (files, APIs, databases, etc.).
    """

    @abstractmethod
    def load(self, source_id: str, **kwargs) -> dict[str, Any]:
        """Load configuration from this source.

        Args:
            source_id: Identifier for the configuration (e.g., file path, API endpoint)
            **kwargs: Additional source-specific parameters

        Returns:
            Dictionary containing the configuration data

        Raises:
            ConfigSourceError: If configuration cannot be loaded
        """
        pass

    @abstractmethod
    def supports(self, source_id: str) -> bool:
        """Check if this source can handle the given identifier.

        Args:
            source_id: Identifier to check

        Returns:
            True if this source can load the configuration
        """
        pass


class ConfigSourceError(Exception):
    """Raised when a configuration source fails to load config."""

    pass


class ConfigSourceManager:
    """Manages configuration source plugins via stevedore."""

    NAMESPACE = "devgraph_integrations.config.sources"
    DEFAULT_SOURCE = "file"

    def __init__(self):
        """Initialize the config source manager and load plugins."""
        self._sources: dict[str, ConfigSource] = {}
        self._load_plugins()

    def _load_plugins(self):
        """Load configuration source plugins using stevedore."""

        def on_load_failure(manager, entrypoint, exception):
            logger.warning(
                f"Failed to load config source plugin {entrypoint.name}: {exception}"
            )

        try:
            mgr = ExtensionManager(
                namespace=self.NAMESPACE,
                invoke_on_load=True,
                on_load_failure_callback=on_load_failure,
            )

            for ext in mgr:
                source = ext.obj
                if isinstance(source, ConfigSource):
                    self._sources[ext.name] = source
                    logger.debug(f"Loaded config source plugin: {ext.name}")
                else:
                    logger.warning(
                        f"Plugin {ext.name} does not implement ConfigSource interface"
                    )
        except RuntimeError as e:
            # No plugins found - this is fine for OSS version
            logger.debug(f"No config source plugins found: {e}")

    def get_source(
        self, source_type: str | None = None, source_id: str | None = None
    ) -> ConfigSource:
        """Get a configuration source by type or auto-detect from source_id.

        Args:
            source_type: Explicit source type name (e.g., "file", "api").
                        If None, auto-detects based on source_id.
            source_id: Source identifier (e.g., file path, URL) for auto-detection

        Returns:
            ConfigSource instance

        Raises:
            ConfigSourceError: If no suitable source is found
        """
        # If source type is explicitly specified, use it
        if source_type:
            if source_type in self._sources:
                return self._sources[source_type]
            raise ConfigSourceError(
                f"Config source '{source_type}' not found. "
                f"Available sources: {list(self._sources.keys())}"
            )

        # Auto-detect based on source_id
        if source_id:
            for name, source in self._sources.items():
                if source.supports(source_id):
                    logger.debug(f"Auto-detected config source: {name}")
                    return source

        # Fall back to default source if available
        if self.DEFAULT_SOURCE in self._sources:
            logger.debug(f"Using default config source: {self.DEFAULT_SOURCE}")
            return self._sources[self.DEFAULT_SOURCE]

        raise ConfigSourceError(
            f"No config source found for source_id: {source_id}. "
            f"Available sources: {list(self._sources.keys())}. "
            f"Default source '{self.DEFAULT_SOURCE}' not available."
        )

    def list_sources(self) -> list[str]:
        """List all available configuration source types.

        Returns:
            List of source type names
        """
        return list(self._sources.keys())


# Global config source manager instance
_source_manager: ConfigSourceManager | None = None


def get_config_source_manager() -> ConfigSourceManager:
    """Get the global config source manager instance.

    Returns:
        ConfigSourceManager singleton
    """
    global _source_manager
    if _source_manager is None:
        _source_manager = ConfigSourceManager()
    return _source_manager
