"""GitLab molecule for Devgraph.

This module provides GitLab integration for discovering projects and hosting services
through both discovery providers and Model Context Protocol (MCP) integration.
"""

from .provider import GitlabProvider

__version__ = "1.0.0"
__molecule_metadata__ = {
    "version": __version__,
    "name": "gitlab",
    "display_name": "GitLab",
    "description": "Discover GitLab projects, hosting services, and project metadata",
    "logo": {"reactIcons": "SiGitlab"},  # react-icons identifier (from react-icons/si)
    "homepage_url": "https://gitlab.com",
    "docs_url": "https://docs.gitlab.com",
    "capabilities": [
        "discovery",
        "mcp",
    ],
    "entity_types": [
        "GitLabProject",
        "GitLabHostingService",
    ],
    "relation_types": [
        "GitLabProjectHostedBy",
    ],
    "requires_auth": True,
    "auth_types": ["pat", "oauth"],
    "min_framework_version": "0.1.0",
}

__all__ = ["GitlabProvider", "__version__", "__molecule_metadata__"]

# MCP server is optional - only import if dependencies are available
try:
    from .mcp import GitlabMCPServer  # noqa: F401
    __all__.append("GitlabMCPServer")
except ImportError:
    pass
