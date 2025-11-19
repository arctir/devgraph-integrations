"""Meta molecule facade."""

from typing import Any, Dict, Optional, Type

from devgraph_integrations.core.molecule import Molecule


class MetaMolecule(Molecule):
    """Meta molecule providing discovery capabilities."""

    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "name": "meta",
            "display_name": "Meta",
            "description": "Provides meta entity definitions and schema information for the Devgraph ontology",
            "logo": {"reactIcons": "GrNodes"},
            "capabilities": ["discovery"],
            "entity_types": ["EntityDefinition"],
            "relation_types": [],
            "requires_auth": False,
            "auth_types": [],
            "min_framework_version": "0.1.0",
        }

    @staticmethod
    def get_discovery_provider() -> Optional[Type[Any]]:
        from .provider import MetaProvider

        return MetaProvider
