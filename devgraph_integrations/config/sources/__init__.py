"""Configuration source extension system."""

from devgraph_integrations.config.sources.base import (
    ConfigSource,
    ConfigSourceError,
    ConfigSourceManager,
    get_config_source_manager,
)
from devgraph_integrations.config.sources.file import FileConfigSource

__all__ = [
    "ConfigSource",
    "ConfigSourceError",
    "ConfigSourceManager",
    "get_config_source_manager",
    "FileConfigSource",
]
