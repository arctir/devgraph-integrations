"""FOSSA molecule facade."""

from typing import Any, Dict, Optional, Type

from devgraph_integrations.core.molecule import Molecule


class FossaMolecule(Molecule):
    """FOSSA molecule providing discovery and MCP capabilities."""

    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "name": "fossa",
            "display_name": "FOSSA",
            "description": "Discover FOSSA projects and create relations to repositories",
            "logo": {"reactIcons": "SiFossa"},
            "homepage_url": "https://fossa.com",
            "docs_url": "https://docs.fossa.com",
            "capabilities": ["discovery", "mcp"],
            "entity_types": ["FOSSAProject"],
            "relation_types": ["FOSSAProjectHostedByRepository"],
            "requires_auth": True,
            "auth_types": ["api_token"],
            "min_framework_version": "0.1.0",
        }

    @staticmethod
    def get_discovery_provider() -> Optional[Type[Any]]:
        from .provider import FOSSAProvider

        return FOSSAProvider

    @staticmethod
    def get_mcp_server() -> Optional[Type[Any]]:
        try:
            from .mcp import FOSSAMCPServer

            return FOSSAMCPServer
        except ImportError:
            return None
