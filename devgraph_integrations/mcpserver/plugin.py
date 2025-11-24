from abc import ABC
from typing import Type

from pydantic import BaseModel

from devgraph_integrations.mcpserver.server import DevgraphFastMCP


class DevgraphMCPPlugin(ABC):
    config_type: Type[BaseModel]
    # Plugin metadata - should be set by subclasses
    plugin_fqdn: str = ""  # e.g., "dora.molecules.devgraph.ai"
    static_assets_version: str = "0.0.0"

    def __init__(self, app: DevgraphFastMCP, config: BaseModel):
        if not isinstance(config, self.config_type):
            raise TypeError(
                f"Expected config of type {self.config_type}, got {type(config)}"
            )
        self.app = app
        self.config = config
        self._server_base_url: str | None = None

    def set_server_base_url(self, base_url: str) -> None:
        """Set the server's base URL for static asset resolution."""
        self._server_base_url = base_url.rstrip("/")

    def static_url(self, filename: str) -> str:
        """Build a full URL for a static asset served by this plugin.

        Args:
            filename: The asset filename (e.g., "dora-metrics.js")

        Returns:
            Full URL to the static asset (e.g., "http://localhost:9000/static/dora.molecules.devgraph.ai/0.1.0/dora-metrics.js")
        """
        if not self._server_base_url:
            raise RuntimeError(
                "Server base URL not set. Ensure set_server_base_url() is called during plugin initialization."
            )
        if not self.plugin_fqdn:
            raise RuntimeError(
                f"plugin_fqdn not set for {self.__class__.__name__}. Set it as a class attribute."
            )

        return f"{self._server_base_url}/static/{self.plugin_fqdn}/{self.static_assets_version}/{filename}"

    @classmethod
    def from_config(
        cls, app: DevgraphFastMCP, config_dict: dict
    ) -> "DevgraphMCPPlugin":
        """
        Create a plugin instance from YAML config.

        Args:
            app (DevgraphFastMCP): The MCP server instance
            config_dict (dict): Configuration dictionary

        Returns:
            Plugin: Instantiated plugin with typed config
        """
        try:
            config = cls.config_type(**config_dict)
            return cls(app, config)
        except ValueError as e:
            raise ValueError(f"Invalid config: {e}")
