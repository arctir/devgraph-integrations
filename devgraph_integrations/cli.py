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
    config = None
    try:
        from devgraph_integrations.config.sources import get_config_source_manager

        manager = get_config_source_manager()
        # Default to file if no config_source subcommand specified
        source_type = getattr(args, "config_source", None) or "file"
        source = manager.get_source(source_type=source_type)

        # Build kwargs from args that match the source's CLI args
        kwargs = {}
        if hasattr(source, "get_cli_args"):
            for arg_def in source.get_cli_args():
                dest = arg_def.get("dest") or arg_def.get("flags", [""])[-1].lstrip(
                    "-"
                ).replace("-", "_")
                if hasattr(args, dest):
                    kwargs[dest] = getattr(args, dest)

        # Load config using the source
        config_data = source.load(getattr(args, "config_path", ""), **kwargs)
        config = Config(**config_data)
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

        output = {name: meta.model_dump() for name, meta in molecules.items()}
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
        print(
            f"{meta.display_name:<15} {meta.version:<10} {capabilities:<30} {entity_types}{status}"
        )

    print()


def run_list_config_sources(args):
    """List available config sources."""
    from devgraph_integrations.config.sources import get_config_source_manager

    manager = get_config_source_manager()
    sources = manager.list_sources()

    if args.json:
        import json

        output = {"sources": sources, "count": len(sources)}
        print(json.dumps(output, indent=2))
        return

    print(f"\nAvailable config sources ({len(sources)}):")
    print("=" * 50)

    if not sources:
        print("  (none found)")
    else:
        for source_name in sorted(sources):
            source = manager._sources[source_name]
            source_class = source.__class__.__name__
            source_module = source.__class__.__module__
            print(f"  {source_name:<20} ({source_module}.{source_class})")

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
            has_mcp = any(p.startswith(f"{molecule_name}.") for p in mcp_plugins.keys())

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
        "release_date": (
            datetime.now(timezone.utc).isoformat() if not args.no_timestamp else None
        ),
        "molecules": molecules_list,
        "summary": {
            "total_molecules": len(molecules_list),
            "discovery_providers": sum(
                1 for m in molecules_list if "discovery" in m.get("capabilities", [])
            ),
            "mcp_servers": sum(
                1 for m in molecules_list if "mcp" in m.get("capabilities", [])
            ),
            "deprecated": sum(1 for m in molecules_list if m.get("deprecated", False)),
        },
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
        from devgraph_integrations.config.sources import get_config_source_manager

        manager = get_config_source_manager()
        # Default to file if no config_source subcommand specified
        source_type = getattr(args, "config_source", None) or "file"
        source = manager.get_source(source_type=source_type)

        # Build kwargs from args that match the source's CLI args
        kwargs = {}
        if hasattr(source, "get_cli_args"):
            for arg_def in source.get_cli_args():
                dest = arg_def.get("dest") or arg_def.get("flags", [""])[-1].lstrip(
                    "-"
                ).replace("-", "_")
                if hasattr(args, dest):
                    kwargs[dest] = getattr(args, dest)

        # Load config using the source
        config_data = source.load(getattr(args, "config_path", ""), **kwargs)
        config = Config(**config_data)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    if not config.mcp:
        logger.error("No MCP configuration found in config file")
        sys.exit(1)

    server = DevgraphMCPSever(config.mcp)
    logger.info(f"Starting MCP server on port {config.mcp.port}")
    server.run(reload=args.reload)


def _add_config_source_subparsers(parser, manager, command_name: str):
    """Add config source subcommands to a parser, filtered by command support."""
    # Get sources that support this command
    supported_sources = []
    for source_name in manager.list_sources():
        source = manager._sources[source_name]
        supported_commands = []
        if hasattr(source, "get_supported_commands"):
            supported_commands = source.get_supported_commands()
        # Empty list means all commands supported
        if not supported_commands or command_name in supported_commands:
            supported_sources.append(source_name)

    if not supported_sources:
        return

    # Create subparsers for config sources
    source_subparsers = parser.add_subparsers(
        dest="config_source",
        help="Configuration source (default: file)",
    )

    # Add subparser for each supported source
    for source_name in supported_sources:
        source = manager._sources[source_name]
        source_parser = source_subparsers.add_parser(
            source_name,
            help=f"Use {source_name} configuration source",
        )

        # Add CLI args for this source
        if hasattr(source, "get_cli_args"):
            for arg_def in source.get_cli_args():
                flags = arg_def.pop("flags", None)
                if flags:
                    source_parser.add_argument(*flags, **arg_def)
                    arg_def["flags"] = flags

    # Also add file source args directly to parent for default behavior
    if "file" in supported_sources:
        file_source = manager._sources["file"]
        if hasattr(file_source, "get_cli_args"):
            for arg_def in file_source.get_cli_args():
                flags = arg_def.pop("flags", None)
                if flags:
                    parser.add_argument(*flags, **arg_def)
                    arg_def["flags"] = flags


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

    # Load config source manager
    from devgraph_integrations.config.sources import get_config_source_manager

    manager = get_config_source_manager()

    # Discovery subcommand
    discover_parser = subparsers.add_parser(
        "discover", help="Run entity discovery process"
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

    # Add config source subparsers (must be after other args for default file behavior)
    _add_config_source_subparsers(discover_parser, manager, "discover")

    # MCP server subcommand
    mcp_parser = subparsers.add_parser("mcp", help="Run MCP server")

    mcp_parser.add_argument(
        "-r",
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    # Add config source subparsers
    _add_config_source_subparsers(mcp_parser, manager, "mcp")

    # List molecules subcommand
    list_parser = subparsers.add_parser("list", help="List available molecules")
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # List config sources subcommand
    config_sources_parser = subparsers.add_parser(
        "config-sources", help="List available configuration sources"
    )
    config_sources_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # Release manifest subcommand
    manifest_parser = subparsers.add_parser(
        "release-manifest", help="Generate release manifest JSON for GitHub releases"
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
        elif args.command == "config-sources":
            run_list_config_sources(args)
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
