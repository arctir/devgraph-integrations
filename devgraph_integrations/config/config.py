"""Main configuration class for devgraph-integrations."""

from __future__ import annotations

from loguru import logger

from .base import SensitiveBaseModel
from .discovery import DiscoveryConfig
from .mcp import MCPServerConfig
from .sources import ConfigSourceError, get_config_source_manager


class Config(SensitiveBaseModel):
    """Main configuration for devgraph-integrations."""

    discovery: DiscoveryConfig | None = None
    mcp: MCPServerConfig | None = None

    @staticmethod
    def from_source(source_id: str, source_type: str | None = None, **kwargs) -> Config:
        """Load configuration from a pluggable source.

        Uses stevedore-based extension system to load configuration from various
        sources. The default source is 'file' for file-based configuration.

        Args:
            source_id: Source identifier (e.g., file path, API URL)
            source_type: Optional explicit source type (e.g., "file", "api").
                        If not specified, auto-detects based on source_id or uses default.
            **kwargs: Additional source-specific parameters

        Returns:
            Config instance

        Raises:
            ConfigSourceError: If configuration cannot be loaded
        """
        manager = get_config_source_manager()

        try:
            source = manager.get_source(source_type=source_type, source_id=source_id)
            source_name = source.__class__.__name__
            logger.info(f"Loading configuration from '{source_name}' source")
            data = source.load(source_id, **kwargs)
            return Config(**data)
        except ConfigSourceError as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    @staticmethod
    def from_config_file(config_path: str) -> Config:
        """Load configuration from YAML file.

        Convenience method for backward compatibility.

        Args:
            config_path: Path to the configuration file

        Returns:
            Config instance

        Raises:
            ConfigSourceError: If configuration cannot be loaded
        """
        return Config.from_source(
            config_path, source_type="file", env_prefix="DEVGRAPH_CFG_"
        )
