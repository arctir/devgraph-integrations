"""Provider config versioning and migration support.

This module provides classes and utilities for managing provider config schema
versions, including deprecation tracking and automatic migrations.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

from loguru import logger


@dataclass
class ConfigVersionInfo:
    """Metadata about a config schema version.

    Attributes:
        version: The version number
        deprecated: Whether this version is deprecated
        deprecated_at: When this version was deprecated
        removal_at: When this version will be removed/unsupported
        deprecation_message: Human-readable message about the deprecation
    """

    version: int
    deprecated: bool = False
    deprecated_at: Optional[datetime] = None
    removal_at: Optional[datetime] = None
    deprecation_message: Optional[str] = None

    def is_supported(self) -> bool:
        """Check if this version is still supported."""
        if self.removal_at and datetime.now() > self.removal_at:
            return False
        return True

    def days_until_removal(self) -> Optional[int]:
        """Calculate days until removal."""
        if not self.removal_at:
            return None
        delta = self.removal_at - datetime.now()
        return max(0, delta.days)


class ProviderVersionSupport:
    """Declares which config versions a provider supports.

    This class manages version information, deprecation warnings, and migration
    paths for provider configurations.

    Example:
        VERSION_SUPPORT = ProviderVersionSupport(
            current_version=3,
            supported_versions=[
                ConfigVersionInfo(
                    version=1,
                    deprecated=True,
                    deprecated_at=datetime(2025, 1, 1),
                    removal_at=datetime(2025, 6, 1),
                    deprecation_message="Field names changed"
                ),
                ConfigVersionInfo(version=2, deprecated=True),
                ConfigVersionInfo(version=3),
            ],
            migration_path={
                1: migrate_v1_to_v2,
                2: migrate_v2_to_v3,
            }
        )
    """

    def __init__(
        self,
        current_version: int,
        supported_versions: list[ConfigVersionInfo],
        migration_path: dict[int, Callable[[dict], dict]],
    ):
        """Initialize version support.

        Args:
            current_version: The current/latest config schema version
            supported_versions: List of version info for all supported versions
            migration_path: Map of {from_version: migration_function} for upgrading configs
        """
        self.current_version = current_version
        self.supported_versions = {v.version: v for v in supported_versions}
        self.migration_path = migration_path

        # Validate that current version exists
        if current_version not in self.supported_versions:
            raise ValueError(
                f"Current version {current_version} not in supported versions"
            )

    def is_supported(self, version: int) -> bool:
        """Check if a version is still supported.

        Args:
            version: The version number to check

        Returns:
            True if the version is supported, False otherwise
        """
        if version not in self.supported_versions:
            return False

        version_info = self.supported_versions[version]
        return version_info.is_supported()

    def get_deprecation_warning(self, version: int) -> Optional[str]:
        """Get deprecation warning for a version.

        Args:
            version: The version number to check

        Returns:
            Deprecation warning string, or None if not deprecated
        """
        if version not in self.supported_versions:
            return None

        version_info = self.supported_versions[version]
        if not version_info.deprecated:
            return None

        warning = f"Config version {version} is deprecated."

        if version_info.deprecation_message:
            warning += f" {version_info.deprecation_message}"

        days_left = version_info.days_until_removal()
        if days_left is not None:
            if days_left == 0:
                warning += " Will be removed today!"
            elif days_left <= 30:
                warning += f" Will be removed in {days_left} days!"
            elif version_info.removal_at:
                warning += f" Will be removed on {version_info.removal_at.date()}."

        warning += f" Please migrate to version {self.current_version}."

        return warning

    def migrate_config(self, config: dict, from_version: int) -> dict:
        """Migrate a config from an old version to the current version.

        Args:
            config: The config dictionary to migrate
            from_version: The version to migrate from

        Returns:
            The migrated config dictionary

        Raises:
            ValueError: If no migration path exists or version is unsupported
        """
        if from_version == self.current_version:
            return config.copy()

        if not self.is_supported(from_version):
            raise ValueError(
                f"Config version {from_version} is no longer supported. "
                f"Current version: {self.current_version}"
            )

        if from_version > self.current_version:
            raise ValueError(
                f"Config version {from_version} is newer than current version {self.current_version}. "
                "Please upgrade the provider code."
            )

        # Apply migrations sequentially
        migrated = config.copy()
        current = from_version

        logger.debug(
            f"Migrating config from version {from_version} to {self.current_version}"
        )

        while current < self.current_version:
            migration_func = self.migration_path.get(current)
            if not migration_func:
                raise ValueError(
                    f"No migration path from version {current} to {current + 1}. "
                    f"Migration path: {list(self.migration_path.keys())}"
                )

            logger.debug(f"Applying migration from v{current} to v{current + 1}")
            migrated = migration_func(migrated)
            current += 1

        logger.info(
            f"Successfully migrated config from v{from_version} to v{self.current_version}"
        )
        return migrated

    def get_version_info(self, version: int) -> Optional[ConfigVersionInfo]:
        """Get version info for a specific version.

        Args:
            version: The version number

        Returns:
            ConfigVersionInfo or None if version doesn't exist
        """
        return self.supported_versions.get(version)

    def list_all_versions(self) -> list[ConfigVersionInfo]:
        """Get info for all supported versions.

        Returns:
            List of ConfigVersionInfo sorted by version number
        """
        return sorted(self.supported_versions.values(), key=lambda v: v.version)
