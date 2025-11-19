"""GitHub molecule facade."""

from typing import Any, Dict, Optional, Type

from devgraph_integrations.core.molecule import Molecule


class GithubMolecule(Molecule):
    """GitHub molecule providing discovery and MCP capabilities."""

    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "name": "github",
            "display_name": "GitHub",
            "description": "Discover GitHub repositories, hosting services, and repository metadata",
            "logo": {"reactIcons": "SiGithub"},
            "homepage_url": "https://github.com",
            "docs_url": "https://docs.github.com",
            "capabilities": ["discovery", "mcp"],
            "entity_types": ["GitHubRepository", "GitHubHostingService"],
            "relation_types": ["GitHubRepositoryHostedBy"],
            "requires_auth": True,
            "auth_types": ["pat", "github_app"],
            "min_framework_version": "0.1.0",
        }

    @staticmethod
    def get_discovery_provider() -> Optional[Type[Any]]:
        from .provider import GithubProvider

        return GithubProvider

    @staticmethod
    def get_mcp_server() -> Optional[Type[Any]]:
        try:
            from .mcp import GithubMCPServer

            return GithubMCPServer
        except ImportError:
            return None
