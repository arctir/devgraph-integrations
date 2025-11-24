import logging
import os
from pathlib import Path

# Disable rich logging from fastmcp before importing it
os.environ["RICH_FORCE_TERMINAL"] = "0"

import jwt
from fastmcp.server.http import create_streamable_http_app
from loguru import logger
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse

from devgraph_integrations.config.mcp import MCPServerConfig

from .pluginmanager import DevgraphMCPPluginManager


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to validate JWT tokens on all protected routes."""

    # Routes that don't require authentication
    PUBLIC_PATHS = {"/health", "/mcp/health"}

    def __init__(
        self,
        app,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        jwt_audience: str | None = None,
        jwt_issuer: str | None = None,
    ):
        super().__init__(app)
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.jwt_audience = jwt_audience
        self.jwt_issuer = jwt_issuer

    async def dispatch(self, request: Request, call_next):
        # Skip auth for public paths
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        # Get authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return JSONResponse(
                {"error": "Missing authorization header"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return JSONResponse(
                {
                    "error": "Invalid authorization header format. Expected: Bearer <token>"
                },
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = parts[1]

        # Validate JWT
        try:
            decode_options = {}
            if self.jwt_audience:
                decode_options["audience"] = self.jwt_audience
            if self.jwt_issuer:
                decode_options["issuer"] = self.jwt_issuer

            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                **decode_options,
            )

            # Store decoded payload in request state for downstream use
            request.state.jwt_payload = payload
            request.state.user = payload.get("sub")

            logger.debug(f"JWT validated for user: {payload.get('sub')}")

        except jwt.ExpiredSignatureError:
            return JSONResponse(
                {"error": "Token has expired"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidAudienceError:
            return JSONResponse(
                {"error": "Invalid token audience"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidIssuerError:
            return JSONResponse(
                {"error": "Invalid token issuer"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return JSONResponse(
                {"error": "Invalid token"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)


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
        self._static_assets = {}  # Maps filename -> (plugin_name, filepath)

    def _load_plugins(self, app: FastMCP):
        """
        Loads molecules for the MCP server using the plugin manager.
        """
        for plugin in self.config.molecules:
            logger.debug(
                f"Loading molecule: {plugin.name} {plugin.type} (enabled: {plugin.enabled})"
            )
            if plugin.enabled:
                molecule_cls = self.plugin_manager.plugin_class(plugin.type)
                if molecule_cls:
                    # Get the MCP server class from the molecule
                    if hasattr(molecule_cls, "get_mcp_server"):
                        cls = molecule_cls.get_mcp_server()
                        if cls is None:
                            logger.error(f"Molecule {plugin.type} has no MCP server")
                            raise ValueError(
                                f"Molecule {plugin.type} has no MCP server"
                            )
                    else:
                        cls = molecule_cls

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

                    # Set the server base URL and plugin FQDN for static_url() support
                    if hasattr(instance, "set_server_base_url"):
                        # Use configured base_url if provided, otherwise build from host/port
                        if self.config.base_url:
                            base_url = self.config.base_url.rstrip("/")
                        else:
                            scheme = "http"
                            host = self.config.host
                            port = self.config.port
                            base_url = f"{scheme}://{host}:{port}"
                        instance.set_server_base_url(base_url)
                        # Set the plugin FQDN from the stevedore entry point name
                        instance.plugin_fqdn = plugin.type
                        logger.debug(
                            f"Set server base URL for {plugin.name}: {base_url}"
                        )

                    # Note: Tools are now registered in the molecule's __init__ method
                    # This ensures they are bound methods with proper self references
                    logger.info(
                        f"Plugin {plugin.name} initialized and tools registered"
                    )

                    # Collect static assets from the molecule
                    # Path format: /static/{fqdn}/{version}/{filename}
                    if hasattr(instance, "static_assets") and instance.static_assets:
                        # Use the stevedore entry point name as FQDN (e.g., "dora.molecules.devgraph.ai")
                        fqdn = plugin.type
                        # Get version from class attribute, default to "0.0.0"
                        version = getattr(instance, "static_assets_version", "0.0.0")

                        for filename, filepath in instance.static_assets.items():
                            filepath = Path(filepath)
                            if filepath.exists():
                                # Namespace: {fqdn}/{version}/{filename}
                                namespaced_key = f"{fqdn}/{version}/{filename}"
                                self._static_assets[namespaced_key] = (
                                    plugin.name,
                                    filepath,
                                )
                                logger.info(
                                    f"Registered static asset: /static/{namespaced_key}"
                                )
                            else:
                                logger.warning(
                                    f"Static asset not found: {filepath} from {plugin.name}"
                                )
                else:
                    logger.error(f"Plugin class not found: {plugin.type}")
                    raise ValueError(f"Plugin class not found: {plugin.type}")

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
            return JSONResponse({"status": "healthy"})

        app.add_route("/mcp/health", health_check, methods=["GET"])
        app.add_route("/health", health_check, methods=["GET"])

        # Add static asset serving for molecule components
        static_assets = self._static_assets

        async def serve_static(request):
            """Serve static JS/CSS assets from molecules."""
            filename = request.path_params.get("filename", "")

            if filename in static_assets:
                plugin_name, filepath = static_assets[filename]

                # Determine content type
                content_type = "application/javascript"
                if filename.endswith(".css"):
                    content_type = "text/css"
                elif filename.endswith(".json"):
                    content_type = "application/json"
                elif filename.endswith(".html"):
                    content_type = "text/html"

                return FileResponse(
                    filepath,
                    media_type=content_type,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "public, max-age=3600",
                    },
                )

            return JSONResponse(
                {"error": f"Static asset not found: {filename}"}, status_code=404
            )

        async def list_static(request):
            """List available static assets."""
            return JSONResponse(
                {
                    "assets": [
                        {"filename": f, "plugin": p}
                        for f, (p, _) in static_assets.items()
                    ]
                }
            )

        app.add_route("/static/{filename:path}", serve_static, methods=["GET"])
        app.add_route("/static", list_static, methods=["GET"])

        # Add JWT authentication middleware if enabled (wrap app after routes are added)
        if self.config.jwt_auth.enabled:
            if not self.config.jwt_auth.secret:
                raise ValueError(
                    "JWT authentication is enabled but no secret is configured"
                )

            app.add_middleware(
                JWTAuthMiddleware,
                jwt_secret=self.config.jwt_auth.secret,
                jwt_algorithm=self.config.jwt_auth.algorithm,
                jwt_audience=self.config.jwt_auth.audience,
                jwt_issuer=self.config.jwt_auth.issuer,
            )
            logger.info(
                f"JWT authentication enabled with algorithm: {self.config.jwt_auth.algorithm}"
            )

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
