from loguru import logger
from pluggy import PluginManager

from devgraph_integrations.core.provider import Provider


class DiscoveryExtensionManager:
    def __init__(self):
        self.pm = PluginManager("devgraph.discovery.molecules")
        self.pm.load_setuptools_entrypoints("devgraph.discovery.molecules")
        self.providers = dict([(self.pm.get_name(i), i) for i in self.pm.get_plugins()])
        logger.debug("Loaded discovery molecules: " + ", ".join(self.providers.keys()))

    def provider(self, name: str) -> Provider:
        return self.providers.get(name)
