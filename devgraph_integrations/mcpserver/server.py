import logging
import os

# Disable rich logging from fastmcp before importing it
os.environ["RICH_FORCE_TERMINAL"] = "0"

from fastmcp.server.http import create_streamable_http_app
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from devgraph_integrations.config.mcp import MCPServerConfig

from .pluginmanager import DevgraphMCPPluginManager


class HealthCheckFilter(logging.Filter):
    """Filter to exclude health check endpoints from access logs."""

    def filter(self, record):
        # Filter out health check requests
        if hasattr(record, "getMessage"):
            message = record.getMessage()
            return not any(
                health_path in message for health_path in ["/health", "/mcp/health"]
            )
        return True


class ClosedResourceErrorFilter(logging.Filter):
    """Filter to suppress ClosedResourceError from SSE responses.

    These errors occur when clients disconnect before response completes,
    which is expected behavior and not a real error.
    """

    def filter(self, record):
        # Filter out ClosedResourceError messages
        if hasattr(record, "getMessage"):
            message = record.getMessage()
            if "ClosedResourceError" in message or "SSE response error" in message:
                return False
        # Also check exception info
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            if exc_type and "ClosedResourceError" in str(exc_type):
                return False
        return True


class DevgraphMCPPluginInstance:
    def __init__(self, name: str, instance: object, config: dict | None = None):
        self.name = name
        self.instance = instance
        self.config = config


class MCPAuthContext(BaseModel):
    token: str | None = None
    environment: str | None = None


from fastmcp.server.dependencies import get_http_headers  # noqa: E402


class DevgraphFastMCP(FastMCP):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._additional_http_routes = []

    def _get_additional_http_routes(self):
        """Return additional HTTP routes for the FastMCP server."""
        return self._additional_http_routes

    def _lifespan_manager(self):
        """Provide a lifespan context manager for the server."""
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def lifespan():
            # Startup logic if needed
            yield
            # Shutdown logic if needed

        return lifespan()

    def add_tool(self, tool_func, *args, **kwargs):
        """Override add_tool to handle bound method signatures correctly."""
        # Wrap the tool function for bound methods
        original_func = tool_func
        if hasattr(tool_func, "__self__"):  # It's a bound method
            # For bound methods, create a wrapper that doesn't include 'self' in the signature
            import inspect

            # Get the original signature - inspect.signature() already excludes 'self' for bound methods
            orig_sig = inspect.signature(tool_func)
            params = list(orig_sig.parameters.values())  # Don't skip any parameters
            new_sig = orig_sig.replace(parameters=params)

            def logged_wrapper(*args, **kwargs):
                logger.info(f"TOOL CALL: {tool_func.__name__}({args}, {kwargs})")
                result = original_func(*args, **kwargs)  # Call bound method normally
                return result

            # Copy metadata from original function
            logged_wrapper.__name__ = tool_func.__name__
            logged_wrapper.__doc__ = tool_func.__doc__
            logged_wrapper.__annotations__ = getattr(tool_func, "__annotations__", {})
            logged_wrapper.__signature__ = new_sig  # Set the signature without 'self'

            result = super().add_tool(logged_wrapper, *args, **kwargs)
        else:
            result = super().add_tool(tool_func, *args, **kwargs)

        return result

    def get_auth_context(self) -> MCPAuthContext:
        """Extract AuthContext from the current request or context variable."""
        from contextvars import ContextVar

        # Try to get auth context from context variable first (for parallel execution)
        try:
            _parallel_auth_context: ContextVar = ContextVar(
                "parallel_mcp_auth_context", default=None
            )
            parallel_context = _parallel_auth_context.get()
            if parallel_context:
                logger.info(
                    f"🔍 MCP Server - Using parallel execution auth context: env={parallel_context.environment}"
                )
                return parallel_context
        except Exception as e:
            logger.debug(f"No parallel auth context available: {e}")

        # Fall back to HTTP headers extraction
        headers = get_http_headers()
        logger.info(
            f"🔍 MCP Server get_auth_context - Available headers: {list(headers.keys())}"
        )

        token = None
        authorization = headers.get("authorization")
        if authorization:
            token = authorization.split(" ")[1]
            logger.info(
                f"🔍 MCP Server - Found auth token: {token[:20] if token else 'None'}..."
            )
        else:
            logger.warning("🔍 MCP Server - No authorization header found!")

        environment = headers.get("devgraph-environment", None)
        logger.info(f"🔍 MCP Server - Environment: {environment}")

        return MCPAuthContext(token=token, environment=environment)


# Middleware to set request context (hypothetical)
def auth_middleware(app: DevgraphFastMCP, request):
    """Middleware to set the current request and extract auth data."""
    app.set_current_request(request)
    return request


class DevgraphMCPSever:
    """
    A class representing the Devgraph MCP server.

    Attributes:
        config (Config): Configuration object for the server.
    """

    def __init__(self, config: MCPServerConfig | None):
        """
        Initializes the Devgraph MCP server with the given configuration.

        Args:
            config (Config): Configuration object for the server.
        """
        self.config = config if config is not None else MCPServerConfig()
        self.plugin_manager = DevgraphMCPPluginManager()
        self._plugins = {}

    def _load_plugins(self, app: FastMCP):
        """
        Loads molecules for the MCP server using the plugin manager.
        """
        for plugin in self.config.molecules:
            logger.debug(
                f"Loading molecule: {plugin.name} {plugin.type} (enabled: {plugin.enabled})"
            )
            if plugin.enabled:
                cls = self.plugin_manager.plugin_class(plugin.type)
                if cls:
                    if plugin.config:
                        instance = cls.from_config(app, plugin.config)
                    else:
                        # Create instance with default config if none provided
                        if hasattr(cls, "config_type"):
                            default_config = cls.config_type()
                            instance = cls(app, default_config)
                        else:
                            instance = cls(app)

                    self._plugins[plugin.name] = instance
                    logger.info(f"Loaded molecule: {plugin.name}")

                    # Note: Tools are now registered in the molecule's __init__ method
                    # This ensures they are bound methods with proper self references
                    logger.info(
                        f"Plugin {plugin.name} initialized and tools registered"
                    )
                else:
                    logger.error(f"Plugin class not found: {plugin.plugin}")
                    raise ValueError(f"Plugin class not found: {plugin.plugin}")

    def get_app(self):
        # Configure all logging before creating the app to catch rich logging
        import logging

        from loguru import logger as loguru_logger

        # Intercept handler for stdlib logging
        class InterceptHandler(logging.Handler):
            def emit(self, record):
                try:
                    level = loguru_logger.level(record.levelname).name
                except ValueError:
                    level = record.levelno

                frame, depth = logging.currentframe(), 2
                while frame and frame.f_code.co_filename == logging.__file__:
                    frame = frame.f_back
                    depth += 1

                loguru_logger.opt(depth=depth, exception=record.exc_info).log(
                    level, record.getMessage()
                )

        # Replace all handlers on root logger and relevant loggers
        logging.root.handlers = [InterceptHandler()]
        logging.root.setLevel(logging.INFO)

        # Pre-configure uvicorn and other loggers before they're created
        for logger_name in [
            "uvicorn",
            "uvicorn.access",
            "uvicorn.error",
            "uvicorn.asgi",
            "fastmcp",
            "mcp",
            "rich",
        ]:
            log = logging.getLogger(logger_name)
            log.handlers = [InterceptHandler()]
            log.setLevel(logging.INFO)
            log.propagate = False

        mcp = DevgraphFastMCP(name=self.config.name)
        self._load_plugins(mcp)
        app = create_streamable_http_app(mcp, "/")

        # Add health check endpoints using Starlette's add_route
        async def health_check(request):
            from starlette.responses import JSONResponse

            return JSONResponse({"status": "healthy"})

        app.add_route("/mcp/health", health_check, methods=["GET"])
        app.add_route("/health", health_check, methods=["GET"])

        return app

    def run(self, reload: bool = False):
        from uvicorn import run

        # Configure logging filters
        uvicorn_access = logging.getLogger("uvicorn.access")
        health_filter = HealthCheckFilter()
        uvicorn_access.addFilter(health_filter)

        # Filter out ClosedResourceError from SSE responses
        closed_resource_filter = ClosedResourceErrorFilter()
        for logger_name in ["mcp.server.streamable_http", "fastmcp", "uvicorn"]:
            log = logging.getLogger(logger_name)
            log.addFilter(closed_resource_filter)

        # Get the app (logging interception is set up in get_app())
        app = self.get_app()

        # Run uvicorn with custom log config disabled so our interceptor works
        run(
            app,
            host=self.config.host,
            port=self.config.port,
            reload=reload,
            log_config=None,  # Disable uvicorn's default logging config
        )
