"""GitLab molecule facade."""

from typing import Any, Dict, Optional, Type

from devgraph_integrations.core.molecule import Molecule


class GitlabMolecule(Molecule):
    """GitLab molecule providing discovery and MCP capabilities."""

    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "name": "gitlab",
            "display_name": "GitLab",
            "description": "Discover GitLab projects, hosting services, and project metadata",
            "logo": {"reactIcons": "SiGitlab"},
            "homepage_url": "https://gitlab.com",
            "docs_url": "https://docs.gitlab.com",
            "capabilities": ["discovery", "mcp"],
            "entity_types": ["GitLabProject", "GitLabHostingService"],
            "relation_types": ["GitLabProjectHostedBy"],
            "requires_auth": True,
            "auth_types": ["pat", "oauth"],
            "min_framework_version": "0.1.0",
        }

    @staticmethod
    def get_discovery_provider() -> Optional[Type[Any]]:
        from .provider import GitlabProvider

        return GitlabProvider

    @staticmethod
    def get_mcp_server() -> Optional[Type[Any]]:
        try:
            from .mcp import GitlabMCPServer

            return GitlabMCPServer
        except ImportError:
            return None
