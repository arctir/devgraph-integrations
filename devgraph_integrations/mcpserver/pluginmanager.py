from loguru import logger
from stevedore import ExtensionManager  # type: ignore


class DevgraphMCPPluginManager:
    """Manages MCP plugin discovery and decorated function execution"""

    _tools = {}
    _resources = {}
    _prompts = {}

    def __init__(self, namespace="devgraph.mcpserver.plugins"):
        self.namespace = namespace
        self._plugin_classes = {}
        self._plugin_class_paths = {}
        self._plugins = {}
        self._load_plugins()

    @classmethod
    def mcp_tool(cls, fn):
        cls._tools[cls._fullname(fn)] = fn
        return fn

    @classmethod
    def mcp_resource(cls, uri: str):
        def decorator(fn):
            cls._resources[cls._fullname(fn)] = fn
            return fn

        return decorator

    def get_tools_by_plugin(self, plugin_name):
        tools = []
        classpath = self.plugin_class_path(plugin_name)
        for name, func in self._tools.items():
            if name.startswith(classpath):
                tools.append(func)
        return tools

    def get_resources_by_plugin(self, plugin_name):
        resources = []
        classpath = self.plugin_class_path(plugin_name)
        for name, func in self._resources.items():
            if name.startswith(classpath):
                resources.append(func)
        return resources

    @classmethod
    def _fullname(cls, func):
        """Get the full qualified name of a function"""
        return f"{func.__module__}.{func.__qualname__}"

    def _load_plugins(self):
        """Load plugins using Stevedore"""

        def on_load_failure(manager, entrypoint, exception):
            logger.error(f"Failed to load plugin {entrypoint}: {exception}")

        mgr = ExtensionManager(
            namespace=self.namespace,
            invoke_on_load=False,
            on_load_failure_callback=on_load_failure,
        )

        for ext in mgr:
            module = ext.plugin
            self._plugin_classes[ext.name] = module
            self._plugin_class_paths[ext.name] = self._fullname(module)
            self._plugins[ext.name] = module

    def plugin_class(self, plugin_name):
        """Get the plugin class by name"""
        return self._plugin_classes.get(plugin_name)

    def plugin_class_path(self, plugin_name):
        """Get the plugin class path by name"""
        return self._plugin_class_paths.get(plugin_name)
