from typing import Any, Callable

from mcp.server.fastmcp.resources.base import Resource  # type: ignore
from mcp.server.fastmcp.resources.resource_manager import (
    ResourceManager,  # type: ignore
)
from pydantic import AnyUrl


class DevgraphResourceManager(ResourceManager):
    def __init__(self, instance, warn_on_duplicate_resources: bool = True):
        super().__init__(warn_on_duplicate_resources=warn_on_duplicate_resources)
        self.resource_instances: dict[str, Any] = {}

    def add_resource(
        self,
        instance: object,
        fn: Callable[..., Any],
        name: str | None = None,
        description: str | None = None,
    ) -> Resource:
        if name:
            self.resource_instances[name] = instance
        return super().add_resource(
            Resource(
                uri=AnyUrl(name) if name else AnyUrl("resource://unnamed"),
                name=name if name else "unnamed",
                description=description if description else "No description",
                # type=type(fn).__name__,
            )
        )

    def add_template(
        self,
        instance: object,
        fn: Callable[..., Any],
        uri_template: str,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
    ) -> Resource:
        if name:
            self.resource_instances[name] = instance
        return super().add_template(
            fn,
            uri_template=uri_template,
            name=name,
            title=title,
            description=description,
            mime_type=mime_type,
        )
        # resource = Resource(
        #    uri=AnyUrl(name) if name else AnyUrl("resource://unnamed"),
        #    name=name if name else "unnamed",
        #    description=description if description else "No description",
        #    type=type(fn).__name__,
        # )
        # return super().add_resource(resource)

    async def get_resource(self, uri: AnyUrl | str) -> Resource | None:
        pass
