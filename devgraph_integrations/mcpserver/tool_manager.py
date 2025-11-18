from typing import Any, Callable

from mcp.server.fastmcp.tools.base import Tool  # type: ignore
from mcp.server.fastmcp.tools.tool_manager import ToolManager  # type: ignore


class DevgraphToolManager(ToolManager):
    def __init__(self, instance, warn_on_duplicate_tools: bool = True):
        super().__init__(warn_on_duplicate_tools=warn_on_duplicate_tools)
        self.tool_instances: dict[str, Any] = {}

    def add_tool(
        self,
        instance: object,
        fn: Callable[..., Any],
        name: str | None = None,
        description: str | None = None,
    ) -> Tool:
        if name:
            self.tool_instances[name] = instance
        return super().add_tool(fn, name, description)

    def call_tool(self, name, arguments, context=None, **kwargs):
        if name and name in self.tool_instances:
            instance = self.tool_instances[name]
            arguments["self"] = instance
        return super().call_tool(
            name,
            arguments,
            context,
            convert_result=True,
        )
