"""Meta entities provider.

This provider exposes the meta entity definitions (Person, Team, Workstream)
as entity definitions that can be discovered and used by other providers.
"""

from typing import Any, Dict, List

from devgraph_integrations.core.provider import DefinitionOnlyProvider
from devgraph_integrations.types.meta import (
    V1PersonEntityDefinition,
    V1ProjectEntityDefinition,
    V1TeamEntityDefinition,
)


class MetaProvider(DefinitionOnlyProvider):
    """Provider for meta entity definitions.

    This provider doesn't discover entities from external systems, but rather
    provides the meta entity definitions themselves so they can be registered
    in the Devgraph system.
    """

    def __init__(self, name: str, every: int, meta_types: List[str] = None) -> None:
        """Initialize meta provider.

        Args:
            name: Provider name
            every: Interval (not used since this provider doesn't run periodically)
            meta_types: Optional list of meta types to create. If None, creates all.
        """
        super().__init__(name, every)
        # Default to all meta types if none specified
        self.meta_types = meta_types or [
            "Person",
            "Team",
            "Workstream",
        ]

    def _should_init_client(self) -> bool:
        """Meta provider doesn't need a client."""
        return False

    def _init_client(self, config) -> None:
        """Meta provider doesn't need a client."""
        return None

    def entity_definitions(self):
        """Return meta entity definitions.

        Returns:
            List of meta entity definitions that can be used by other providers
        """
        return [
            V1PersonEntityDefinition(),
            V1TeamEntityDefinition(),
            V1ProjectEntityDefinition(),  # Workstream
        ]

    @classmethod
    def from_config(cls, config):
        """Create provider from configuration.

        Args:
            config: Provider configuration with optional meta_types list

        Returns:
            MetaProvider instance
        """
        # Extract meta_types from config if provided
        meta_types = getattr(config, "meta_types", None)
        if hasattr(config, "config") and config.config:
            meta_types = config.config.get("meta_types", meta_types)

        return cls(name=config.name, every=config.every, meta_types=meta_types)

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get provider metadata.

        Returns:
            Dict containing provider metadata
        """
        return {
            "type": "meta",
            "display_name": "Meta Entities",
            "description": "Provides meta entity definitions (Person, Team, Project)",
            "config_schema": {
                "type": "object",
                "properties": {
                    "meta_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of meta types to enable",
                        "default": ["Person", "Team", "Workstream"],
                    }
                },
            },
        }

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Get configuration JSON schema.

        Returns:
            JSON schema for provider configuration
        """
        return cls.get_metadata()["config_schema"]
