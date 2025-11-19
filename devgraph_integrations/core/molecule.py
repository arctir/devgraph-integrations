"""Base class for molecule plugins.

A Molecule is a unified plugin that can provide multiple capabilities:
- discovery: Entity discovery provider
- mcp: MCP server for AI integrations
- relations: Relationship discovery between entities

Each molecule registers once under the 'devgraph.molecules' namespace and
declares its available capabilities.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type


class Molecule(ABC):
    """Base class for molecule plugins.

    Molecules are the primary extension point for devgraph integrations.
    Each molecule can provide multiple capabilities (discovery, mcp, etc.)
    and is registered once in the 'devgraph.molecules' namespace.

    Example:
        class GithubMolecule(Molecule):
            @staticmethod
            def get_metadata() -> dict:
                return {
                    "name": "github",
                    "display_name": "GitHub",
                    "capabilities": ["discovery", "mcp"],
                    ...
                }

            @staticmethod
            def get_discovery_provider():
                from .provider import GithubProvider
                return GithubProvider

            @staticmethod
            def get_mcp_server():
                from .mcp import GithubMCPServer
                return GithubMCPServer
    """

    @staticmethod
    @abstractmethod
    def get_metadata() -> Dict[str, Any]:
        """Return molecule metadata.

        Returns:
            Dictionary with metadata fields:
                - name: Machine-readable name (required)
                - display_name: Human-readable name (required)
                - description: Brief description (required)
                - version: Semantic version (required)
                - capabilities: List of capabilities (required)
                - logo: Logo dict with reactIcons/url/svg keys
                - entity_types: List of entity types created
                - relation_types: List of relation types created
                - requires_auth: Whether auth is required
                - auth_types: Supported auth types
        """
        pass

    @staticmethod
    def get_discovery_provider() -> Optional[Type[Any]]:
        """Return the discovery provider class for this molecule.

        Returns:
            Provider class if molecule has discovery capability, None otherwise.
        """
        return None

    @staticmethod
    def get_mcp_server() -> Optional[Type[Any]]:
        """Return the MCP server class for this molecule.

        Returns:
            MCP server class if molecule has mcp capability, None otherwise.
        """
        return None

    @classmethod
    def has_capability(cls, capability: str) -> bool:
        """Check if this molecule has a specific capability.

        Args:
            capability: Capability name (e.g., 'discovery', 'mcp')

        Returns:
            True if molecule has the capability.
        """
        metadata = cls.get_metadata()
        return capability in metadata.get("capabilities", [])

    @classmethod
    def list_capabilities(cls) -> List[str]:
        """List all capabilities this molecule provides.

        Returns:
            List of capability names.
        """
        metadata = cls.get_metadata()
        return metadata.get("capabilities", [])
