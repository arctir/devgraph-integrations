"""Base configuration classes with sensitive field masking."""

import re
from typing import Any, ClassVar, Dict, Set

from pydantic import BaseModel


class SensitiveBaseModel(BaseModel):
    """Base model that automatically masks sensitive fields when displayed."""

    # Pattern to match sensitive field names
    SENSITIVE_PATTERNS: ClassVar[Set[str]] = {
        r".*token.*",
        r".*key.*",
        r".*secret.*",
        r".*password.*",
        r".*credential.*",
        r".*auth.*",
        r".*jwt.*",
    }

    @classmethod
    def _is_sensitive_field(cls, field_name: str) -> bool:
        """Check if a field name matches sensitive patterns."""
        field_lower = field_name.lower()
        return any(
            re.match(pattern, field_lower, re.IGNORECASE)
            for pattern in cls.SENSITIVE_PATTERNS
        )

    def _mask_value(self, value: Any) -> str:
        """Mask a sensitive value for display."""
        if value is None:
            return "None"

        str_value = str(value)
        if len(str_value) <= 8:
            return "***"
        else:
            # Show first 3 and last 3 characters with asterisks in between
            return f"{str_value[:3]}***{str_value[-3:]}"

    def _mask_dict_recursive(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively mask sensitive fields in a dictionary."""
        masked = {}
        for key, value in data.items():
            if self._is_sensitive_field(key):
                masked[key] = self._mask_value(value)  # type: ignore[assignment]
            elif isinstance(value, dict):
                masked[key] = self._mask_dict_recursive(value)  # type: ignore[assignment]
            elif isinstance(value, list):
                masked[key] = [  # type: ignore[assignment]
                    self._mask_dict_recursive(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                masked[key] = value
        return masked

    def model_dump_masked(self, **kwargs) -> Dict[str, Any]:
        """Dump model data with sensitive fields masked."""
        data = self.model_dump(**kwargs)
        return self._mask_dict_recursive(data)

    def __str__(self) -> str:
        """String representation with masked sensitive fields."""
        return f"{self.__class__.__name__}({self.model_dump_masked()})"

    def __repr__(self) -> str:
        """String representation with masked sensitive fields."""
        return self.__str__()


def mask_sensitive_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Utility function to mask sensitive fields in any config dictionary."""
    model = SensitiveBaseModel()
    return model._mask_dict_recursive(config_dict)
