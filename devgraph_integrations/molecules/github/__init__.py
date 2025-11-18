"""GitHub molecule for Devgraph.

This module provides GitHub integration for discovering repositories and hosting services
through both discovery providers and Model Context Protocol (MCP) integration.
"""

from .provider import GithubProvider

__version__ = "1.0.0"
__molecule_metadata__ = {
    "version": __version__,
    "name": "github",
    "display_name": "GitHub",
    "description": "Discover GitHub repositories, hosting services, and repository metadata",
    "logo": {"reactIcons": "SiGithub"},  # react-icons identifier (from react-icons/si)
    "homepage_url": "https://github.com",
    "docs_url": "https://docs.github.com",
    "capabilities": [
        "discovery",
        "mcp",
    ],
    "entity_types": [
        "GitHubRepository",
        "GitHubHostingService",
    ],
    "relation_types": [
        "GitHubRepositoryHostedBy",
    ],
    "requires_auth": True,
    "auth_types": ["pat", "github_app"],
    "min_framework_version": "0.1.0",
}

__all__ = ["GithubProvider", "__version__", "__molecule_metadata__"]

# MCP server is optional - only import if dependencies are available
try:
    from .mcp import GithubMCPServer  # noqa: F401
    __all__.append("GithubMCPServer")
except ImportError:
    pass
