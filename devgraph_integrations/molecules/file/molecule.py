"""File molecule facade."""

from typing import Any, Dict, Optional, Type

from devgraph_integrations.core.molecule import Molecule


class FileMolecule(Molecule):
    """File molecule providing discovery capabilities."""

    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "name": "file",
            "display_name": "File",
            "description": "Read entities and relations from .devgraph.yaml files on disk",
            "logo": {"reactIcons": "PiFile"},
            "capabilities": ["discovery"],
            "entity_types": [],  # Dynamic based on file contents
            "relation_types": [],  # Dynamic based on file contents
            "requires_auth": False,
            "auth_types": [],
            "min_framework_version": "0.1.0",
        }

    @staticmethod
    def get_discovery_provider() -> Optional[Type[Any]]:
        from .provider import FileProvider

        return FileProvider
