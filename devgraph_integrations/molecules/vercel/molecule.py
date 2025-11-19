"""Vercel molecule facade."""

from typing import Any, Dict, Optional, Type

from devgraph_integrations.core.molecule import Molecule


class VercelMolecule(Molecule):
    """Vercel molecule providing discovery capabilities."""

    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "name": "vercel",
            "display_name": "Vercel",
            "description": "Discover Vercel deployments, projects, and teams",
            "logo": {"reactIcons": "SiVercel"},
            "homepage_url": "https://vercel.com",
            "docs_url": "https://vercel.com/docs",
            "capabilities": ["discovery"],
            "entity_types": ["VercelDeployment", "VercelProject", "VercelTeam"],
            "relation_types": [
                "VercelDeploymentBelongsToProject",
                "VercelProjectBelongsToTeam",
            ],
            "requires_auth": True,
            "auth_types": ["api_token"],
            "min_framework_version": "0.1.0",
        }

    @staticmethod
    def get_discovery_provider() -> Optional[Type[Any]]:
        from .provider import VercelProvider

        return VercelProvider
