"""Meta entities molecule provider.

This module provides the meta entity definitions as discoverable entities
in the Devgraph system.
"""

from .provider import MetaProvider

__version__ = "1.0.0"
__molecule_metadata__ = {
    "version": __version__,
    "name": "meta",
    "display_name": "Meta",
    "description": "Provides meta entity definitions and schema information for the Devgraph ontology",
    "logo": {"reactIcons": "GrNodes"},
    "capabilities": [
        "discovery",
    ],
    "entity_types": [
        "EntityDefinition",
    ],
    "relation_types": [],
    "requires_auth": False,
    "auth_types": [],
    "min_framework_version": "0.1.0",
}

__all__ = ["MetaProvider", "__version__", "__molecule_metadata__"]
