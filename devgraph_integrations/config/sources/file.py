"""File-based configuration source.

This is the default configuration source for the OSS version.
"""

from __future__ import annotations

import os
import pathlib
from typing import Any

import yaml  # type: ignore
from loguru import logger

from devgraph_integrations.config.sources.base import ConfigSource, ConfigSourceError


def override_with_env(config: dict, prefix: str = "") -> dict:
    """Override configuration with environment variables.

    Args:
        config: Configuration dictionary to modify
        prefix: Environment variable prefix

    Returns:
        Modified configuration dictionary
    """
    # Process existing keys in config
    for key, value in config.items():
        env_key = (prefix + key).upper()
        if isinstance(value, dict):
            override_with_env(value, env_key + "_")
        elif env_key in os.environ:
            config[key] = os.environ[env_key]

    # Add new fields (including nested) from environment variables
    for env_key, env_value in os.environ.items():
        if env_key.startswith(prefix.upper()):
            # Convert env key to config key path (remove prefix and split by underscore)
            key_path = env_key[len(prefix) :].lower().split("_")
            if not key_path:
                continue

            # Navigate or create nested structure
            current = config
            for i, key in enumerate(key_path[:-1]):
                # If key doesn't exist, create a new dict
                if key not in current:
                    current[key] = {}
                # Ensure the current level is a dict
                if not isinstance(current[key], dict):
                    logger.warning(
                        f"Overwriting non-dict {key} with dict for {env_key}"
                    )
                    current[key] = {}
                current = current[key]

            # Set the final key's value
            final_key = key_path[-1]
            if final_key not in current:
                logger.info(
                    f"Adding new field from environment: {env_key} -> {'.'.join(key_path)}"
                )
            current[final_key] = env_value

    return config


class FileConfigSource(ConfigSource):
    """Load configuration from YAML files.

    This is the default configuration source for OSS deployments.
    """

    @staticmethod
    def get_cli_args() -> list[dict]:
        """Return CLI arguments for file config source."""
        return [
            {
                "flags": ["-c", "--config"],
                "help": "Path to YAML configuration file",
                "default": "/etc/devgraph/config.yaml",
                "dest": "config_path",
            },
        ]

    def supports(self, source_id: str) -> bool:
        """Check if source_id is a file path.

        Args:
            source_id: Potential file path

        Returns:
            True if source_id looks like a file path
        """
        # Support .yaml and .yml files
        return source_id.endswith((".yaml", ".yml")) or os.path.exists(source_id)

    def load(self, source_id: str, **kwargs) -> dict[str, Any]:
        """Load configuration from a YAML file.

        Args:
            source_id: Path to the YAML configuration file (can be overridden by DEVGRAPH_FILE_CONFIG_PATH env var)
            **kwargs: Additional parameters (env_prefix for environment overrides)

        Returns:
            Configuration dictionary

        Raises:
            ConfigSourceError: If file doesn't exist or YAML is invalid
        """
        # Allow source_id to be overridden by environment variable
        config_path = os.getenv("DEVGRAPH_FILE_CONFIG_PATH", source_id)
        if not config_path:
            raise ConfigSourceError(
                "Config path not specified. Set DEVGRAPH_FILE_CONFIG_PATH env var or pass source_id"
            )

        path = pathlib.Path(config_path.strip())
        if not path.exists():
            raise ConfigSourceError(f"Config file not found: {config_path}")

        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError as e:
            raise ConfigSourceError(f"Invalid YAML in {source_id}: {e}")

        # Apply environment variable overrides (hidden option, not exposed in CLI)
        env_prefix = kwargs.get("env_prefix", "DEVGRAPH_CFG_")
        if env_prefix:
            data = override_with_env(data, env_prefix)

        logger.debug(f"Loaded configuration from file: {config_path}")
        return data
