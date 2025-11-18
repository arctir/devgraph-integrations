import os
from .server import DevgraphMCPSever
from devgraph_integrations.config import Config

config_path = os.getenv("DEVGRAPH_CONFIG", "/etc/devgraph/config.yaml")

config = Config.from_config_file(config_path)
server = DevgraphMCPSever(config.mcp)
app = server.get_app()
