import os
from argparse import Namespace

import dotenv  # type: ignore
import ipinfo  # type: ignore
from mcp.server.fastmcp import FastMCP  # type: ignore
from pydantic import BaseModel, ConfigDict, IPvAnyAddress

dotenv.load_dotenv()

# Create MCP server
mcp = FastMCP("BasicServer", port=9000)


class IPDetails(BaseModel):
    ip: IPvAnyAddress = None  # type: ignore
    hostname: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    loc: str | None = None
    timezone: str | None = None

    model_config = ConfigDict(extra="ignore")


@mcp.tool()
async def fetch_ipinfo(ip: str | None = None, **kwargs) -> IPDetails:
    """Get the detailed information of a specified IP address

    Args:
        ip(str or None): The IP address to get information for. Follow the format like 192.168.1.1 .
        **kwargs: Additional keyword arguments to pass to the IPInfo handler.
    Returns:
        IPDetails: The detailed information of the specified IP address.
    """
    handler = ipinfo.getHandler(
        access_token=os.environ.get("IPINFO_API_TOKEN", None),
        headers={"user-agent": "basic-mcp-server", "custom_header": "yes"},
        **kwargs,
    )

    details = handler.getDetails(ip_address=ip)

    return IPDetails(**details.all)


def run_server(args: Namespace):
    mcp.run(args.server_type)


if __name__ == "__main__":
    mcp.run("sse")
