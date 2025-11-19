"""CLI for devgraph-integrations.

To suppress deprecation warnings from third-party dependencies (uvicorn/websockets),
run with: python -W ignore::DeprecationWarning -m devgraph_integrations.cli
or set: export PYTHONWARNINGS="ignore::DeprecationWarning"
"""

import argparse
import asyncio
import sys

from loguru import logger

from devgraph_integrations.config import Config
from devgraph_integrations.core.discovery import DiscoveryProcessor
from devgraph_integrations.core.metadata import list_all_molecules


async def run_discover(args):
    """Run discovery process."""
    path = args.config_path
    config = None
    try:
        # Check if a config source type is specified via environment variable
        source_type = os.getenv("DEVGRAPH_CONFIG_SOURCE")
        if source_type:
            logger.debug(f"Using config source type from environment: {source_type}")
            config = Config.from_source(path, source_type=source_type)
        else:
            config = Config.from_config_file(path)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    processor = DiscoveryProcessor(config, provider_names=args.molecules)
    processor.create_entity_definitions()

    # Run the blocking discover() in a thread pool to allow cancellation
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, processor.discover, args.oneshot)
    except KeyboardInterrupt:
        logger.info("Discovery interrupted by user")
        raise


def run_list_molecules(args):
    """List available molecules and their metadata."""
    molecules = list_all_molecules()

    if not molecules:
        print("No molecules found")
        return

    if args.json:
        import json
        output = {
            name: meta.model_dump() for name, meta in molecules.items()
        }
        print(json.dumps(output, indent=2))
        return

    # Table format
    print(f"\n{'Molecule':<15} {'Version':<10} {'Capabilities':<30} {'Entity Types'}")
    print("=" * 100)

    for name, meta in sorted(molecules.items()):
        capabilities = ", ".join(meta.capabilities[:3])
        if len(meta.capabilities) > 3:
            capabilities += "..."

        entity_types = ", ".join(meta.entity_types[:2])
        if len(meta.entity_types) > 2:
            entity_types += f" (+{len(meta.entity_types) - 2})"

        status = " (deprecated)" if meta.deprecated else ""
        print(f"{meta.display_name:<15} {meta.version:<10} {capabilities:<30} {entity_types}{status}")

    print()


def run_release_manifest(args):
    """Generate a release manifest JSON for GitHub releases."""
    import json
    import tomllib
    from datetime import datetime, timezone
    from pathlib import Path

    # Load package version from pyproject.toml
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    package_version = pyproject["tool"]["poetry"]["version"]

    # Get all molecule metadata (those with __molecule_metadata__)
    molecules = list_all_molecules()

    # Get registered plugins from pyproject.toml to find all molecules
    discovery_plugins = pyproject["tool"]["poetry"]["plugins"].get(
        "devgraph.discovery.molecules", {}
    )
    mcp_plugins = pyproject["tool"]["poetry"]["plugins"].get(
        "devgraph.mcpserver.plugins", {}
    )

    # Build set of all registered molecule names
    all_molecule_names = set()
    for plugin_name in discovery_plugins.keys():
        molecule_name = plugin_name.split(".")[0]
        all_molecule_names.add(molecule_name)
    for plugin_name in mcp_plugins.keys():
        molecule_name = plugin_name.split(".")[0]
        all_molecule_names.add(molecule_name)

    # Create molecules list with metadata or fallback info
    molecules_list = []
    for molecule_name in sorted(all_molecule_names):
        if molecule_name in molecules:
            # Has full metadata
            molecule_data = molecules[molecule_name].model_dump()
        else:
            # Create minimal metadata from plugin registry
            has_discovery = any(
                p.startswith(f"{molecule_name}.") for p in discovery_plugins.keys()
            )
            has_mcp = any(
                p.startswith(f"{molecule_name}.") for p in mcp_plugins.keys()
            )

            capabilities = []
            if has_discovery:
                capabilities.append("discovery")
            if has_mcp:
                capabilities.append("mcp")

            molecule_data = {
                "version": package_version,
                "name": molecule_name,
                "display_name": molecule_name.capitalize(),
                "description": f"{molecule_name.capitalize()} integration provider",
                "logo": None,
                "homepage_url": None,
                "docs_url": None,
                "capabilities": capabilities,
                "entity_types": [],
                "relation_types": [],
                "requires_auth": True,
                "auth_types": [],
                "min_framework_version": "0.1.0",
                "deprecated": False,
                "replacement": None,
            }

        molecules_list.append(molecule_data)

    # Build the manifest
    manifest = {
        "package": "devgraph-integrations",
        "version": package_version,
        "release_date": datetime.now(timezone.utc).isoformat() if not args.no_timestamp else None,
        "molecules": molecules_list,
        "summary": {
            "total_molecules": len(molecules_list),
            "discovery_providers": sum(1 for m in molecules_list if "discovery" in m.get("capabilities", [])),
            "mcp_servers": sum(1 for m in molecules_list if "mcp" in m.get("capabilities", [])),
            "deprecated": sum(1 for m in molecules_list if m.get("deprecated", False)),
        }
    }

    print(json.dumps(manifest, indent=2))


def run_mcp(args):
    """Run MCP server."""
    try:
        from devgraph_integrations.mcpserver.server import DevgraphMCPSever
    except ImportError:
        logger.error(
            "MCP server dependencies not installed. "
            "Install with: pip install devgraph-integrations[mcp]"
        )
        sys.exit(1)

    try:
        # Check if a config source type is specified via environment variable
        source_type = os.getenv("DEVGRAPH_CONFIG_SOURCE")
        if source_type:
            logger.debug(f"Using config source type from environment: {source_type}")
            config = Config.from_source(args.config_path, source_type=source_type)
        else:
            config = Config.from_config_file(args.config_path)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    if not config.mcp:
        logger.error("No MCP configuration found in config file")
        sys.exit(1)

    server = DevgraphMCPSever(config.mcp)
    logger.info(f"Starting MCP server on port {config.mcp.port}")
    server.run(reload=args.reload)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Devgraph Integrations - Discover and sync entities"
    )
    parser.add_argument(
        "-l",
        "--log-level",
        help="Select log level",
        default="INFO",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Discovery subcommand
    discover_parser = subparsers.add_parser(
        "discover", help="Run entity discovery process"
    )
    discover_parser.add_argument(
        "-c",
        "--config-path",
        default=os.getenv("DEVGRAPH_CONFIG_PATH", "/etc/devgraph/config.yaml"),
        type=str,
        help="Path to the config file",
    )
    discover_parser.add_argument(
        "-o",
        "--oneshot",
        action="store_true",
        help="Run the discovery process once and exit",
    )
    discover_parser.add_argument(
        "-p",
        "--molecules",
        nargs="+",
        type=str,
        default=None,
        help="Specific molecules to run (runs all if not specified)",
    )

    # MCP server subcommand
    mcp_parser = subparsers.add_parser("mcp", help="Run MCP server")
    mcp_parser.add_argument(
        "-c",
        "--config-path",
        default=os.getenv("DEVGRAPH_CONFIG_PATH", "/etc/devgraph/config.yaml"),
        type=str,
        help="Path to the config file",
    )
    mcp_parser.add_argument(
        "-r",
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    # List molecules subcommand
    list_parser = subparsers.add_parser("list", help="List available molecules")
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # Release manifest subcommand
    manifest_parser = subparsers.add_parser(
        "release-manifest",
        help="Generate release manifest JSON for GitHub releases"
    )
    manifest_parser.add_argument(
        "--no-timestamp",
        action="store_true",
        help="Omit timestamp from manifest (useful for reproducible builds)",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()

    # Configure logging
    logger.remove()
    logger.add(sys.stdout, level=args.log_level.upper())

    if not args.command:
        logger.error("No command specified. Use 'discover' or 'mcp'")
        sys.exit(1)

    try:
        if args.command == "discover":
            asyncio.run(run_discover(args))
        elif args.command == "mcp":
            run_mcp(args)
        elif args.command == "list":
            run_list_molecules(args)
        elif args.command == "release-manifest":
            run_release_manifest(args)
    except KeyboardInterrupt:
        logger.info("Interrupted by user (Ctrl+C)")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
