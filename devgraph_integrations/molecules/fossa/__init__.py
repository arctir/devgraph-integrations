"""FOSSA molecule for Devgraph.

This module provides FOSSA integration for retrieving SBOM and license data
through the Model Context Protocol (MCP) and discovery of FOSSA projects.
"""

from .provider import FOSSAProvider

__version__ = "1.0.0"
__molecule_metadata__ = {
    "version": __version__,
    "name": "fossa",
    "display_name": "FOSSA",
    "description": "Discover FOSSA projects and create relations to repositories",
    "logo": {"reactIcons": "SiFossa"},  # react-icons identifier (from react-icons/si)
    "homepage_url": "https://fossa.com",
    "docs_url": "https://docs.fossa.com",
    "capabilities": [
        "discovery",
        "mcp",
    ],
    "entity_types": [
        "FOSSAProject",
    ],
    "relation_types": [
        "FOSSAProjectHostedByRepository",
    ],
    "requires_auth": True,
    "auth_types": ["api_token"],
    "min_framework_version": "0.1.0",
}

__all__ = ["FOSSAProvider", "__version__", "__molecule_metadata__"]

# MCP server is optional - only import if dependencies are available
try:
    from .mcp import FOSSAMCPServer  # noqa: F401

    __all__.append("FOSSAMCPServer")
except ImportError:
    pass
