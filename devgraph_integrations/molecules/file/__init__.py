"""File provider for Devgraph molecule framework.

This module implements a provider that reads entities and relations from
.devgraph.yaml files on disk.
"""

from .provider import FileProvider
from .config import FileProviderConfig

__version__ = "1.0.0"
__molecule_metadata__ = {
    "version": __version__,
    "name": "file",
    "display_name": "File",
    "description": "Read entities and relations from .devgraph.yaml files on disk",
    "logo": {"reactIcons": "PiFile"},
    "capabilities": [
        "discovery",
    ],
    "entity_types": [],  # Dynamic based on file contents
    "relation_types": [],  # Dynamic based on file contents
    "requires_auth": False,
    "auth_types": [],
    "min_framework_version": "0.1.0",
}

__all__ = ["FileProvider", "FileProviderConfig", "__version__", "__molecule_metadata__"]
