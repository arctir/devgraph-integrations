import os

from devgraph_integrations.config import Config

from .server import DevgraphMCPSever

config_path = os.getenv("DEVGRAPH_CONFIG", "/etc/devgraph/config.yaml")

config = Config.from_config_file(config_path)
server = DevgraphMCPSever(config.mcp)
app = server.get_app()
