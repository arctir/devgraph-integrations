"""Argo CD molecule facade."""

from typing import Any, Dict, Optional, Type

from devgraph_integrations.core.molecule import Molecule


class ArgoMolecule(Molecule):
    """Argo CD molecule providing discovery capabilities."""

    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "name": "argo",
            "display_name": "Argo CD",
            "description": "Discover Argo CD applications, projects, and instances for GitOps tracking",
            "logo": {"reactIcons": "SiArgocd"},
            "homepage_url": "https://argo-cd.readthedocs.io",
            "docs_url": "https://argo-cd.readthedocs.io/en/stable/",
            "capabilities": ["discovery"],
            "entity_types": ["ArgoApplication", "ArgoProject", "ArgoInstance"],
            "relation_types": [
                "ArgoApplicationBelongsToProject",
                "ArgoApplicationDeployedOn",
            ],
            "requires_auth": True,
            "auth_types": ["api_token"],
            "min_framework_version": "0.1.0",
        }

    @staticmethod
    def get_discovery_provider() -> Optional[Type[Any]]:
        from .provider import ArgoProvider

        return ArgoProvider
