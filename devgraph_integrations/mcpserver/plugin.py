from abc import ABC
from typing import Type

from pydantic import BaseModel
from devgraph_integrations.mcpserver.server import DevgraphFastMCP


class DevgraphMCPPlugin(ABC):
    config_type: Type[BaseModel]

    def __init__(self, app: DevgraphFastMCP, config: BaseModel):
        if not isinstance(config, self.config_type):
            raise TypeError(
                f"Expected config of type {self.config_type}, got {type(config)}"
            )
        self.app = app
        self.config = config

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
