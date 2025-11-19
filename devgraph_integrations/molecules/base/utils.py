"""Utility functions for molecule providers.

This module provides common utility functions that can be shared across
molecule providers to reduce code duplication.
"""

from typing import Any, Dict, List, Optional, Union

from loguru import logger


def safe_get(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Safely get nested dictionary value using dot notation.

    Args:
        data: Dictionary to extract value from
        path: Dot-separated path (e.g., "spec.metadata.name")
        default: Default value if path doesn't exist

    Returns:
        Value at path or default if not found
    """
    try:
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    except Exception:
        return default


def flatten_labels(labels: Dict[str, Any]) -> Dict[str, str]:
    """Flatten complex label values to strings.

    Args:
        labels: Dictionary of label values

    Returns:
        Dictionary with all values converted to strings
    """
    flattened = {}
    for key, value in labels.items():
        if isinstance(value, (list, dict)):
            # Convert complex types to JSON strings
            import json

            try:
                flattened[key] = json.dumps(value, separators=(",", ":"))
            except (TypeError, ValueError):
                flattened[key] = str(value)
        else:
            flattened[key] = str(value)
    return flattened


def sanitize_entity_name(name: str, max_length: int = 63) -> str:
    """Sanitize entity name for DNS 1123 and Cypher compatibility.

    Converts names to be compatible with both DNS 1123 labels and Cypher queries.
    Periods are replaced with hyphens to avoid conflicts with Cypher dot notation.

    Args:
        name: Raw entity name
        max_length: Maximum allowed length

    Returns:
        Sanitized entity name that's DNS 1123 and Cypher-compatible
    """
    import re

    # Convert to lowercase
    name = name.lower()

    # Replace periods with hyphens (avoid Cypher dot notation conflicts)
    name = name.replace(".", "-")

    # Replace invalid characters with hyphens
    name = re.sub(r"[^a-z0-9\-]", "-", name)

    # Remove leading/trailing hyphens
    name = name.strip("-")

    # Collapse multiple hyphens
    name = re.sub(r"-+", "-", name)

    # Truncate if too long
    if len(name) > max_length:
        name = name[:max_length].rstrip("-")

    return name or "unnamed"


def batch_process(
    items: List[Any],
    processor: callable,
    batch_size: int = 100,
    item_name: str = "item",
) -> List[Any]:
    """Process items in batches with progress logging.

    Args:
        items: List of items to process
        processor: Function to process each item
        batch_size: Number of items to process in each batch
        item_name: Name for logging purposes

    Returns:
        List of successfully processed results
    """
    results = []
    total = len(items)

    for i in range(0, total, batch_size):
        batch = items[i : i + batch_size]
        batch_end = min(i + batch_size, total)

        logger.debug(f"Processing {item_name}s {i + 1}-{batch_end} of {total}")

        for item in batch:
            try:
                result = processor(item)
                if result is not None:
                    results.append(result)
            except Exception as e:
                item_id = getattr(item, "id", getattr(item, "name", "unknown"))
                logger.warning(f"Failed to process {item_name} '{item_id}': {e}")
                continue

    logger.info(f"Successfully processed {len(results)} of {total} {item_name}s")
    return results


def parse_url_components(url: str) -> Dict[str, str]:
    """Parse URL into components for relation matching.

    Args:
        url: URL to parse

    Returns:
        Dictionary with URL components (scheme, host, path, etc.)
    """
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
        return {
            "scheme": parsed.scheme,
            "hostname": parsed.hostname or "",
            "port": str(parsed.port) if parsed.port else "",
            "path": parsed.path.strip("/"),
            "full_url": url,
        }
    except Exception as e:
        logger.warning(f"Failed to parse URL '{url}': {e}")
        return {"full_url": url}


def normalize_timestamp(timestamp: Union[str, int, None]) -> Optional[str]:
    """Normalize timestamp to ISO format string.

    Args:
        timestamp: Timestamp in various formats

    Returns:
        ISO format timestamp string or None
    """
    if not timestamp:
        return None

    try:
        from datetime import datetime

        if isinstance(timestamp, str):
            # Try parsing various formats
            for fmt in [
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S%z",
            ]:
                try:
                    dt = datetime.strptime(
                        timestamp.replace("Z", "+00:00"), fmt.replace("Z", "%z")
                    )
                    return dt.isoformat()
                except ValueError:
                    continue

            # If no format matches, return as-is if it looks like ISO
            if "T" in timestamp:
                return timestamp

        elif isinstance(timestamp, int):
            # Assume Unix timestamp
            dt = datetime.fromtimestamp(timestamp)
            return dt.isoformat()

    except Exception as e:
        logger.warning(f"Failed to normalize timestamp '{timestamp}': {e}")

    return None


def merge_configurations(
    base: Dict[str, Any], override: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge configuration dictionaries with override support.

    Args:
        base: Base configuration dictionary
        override: Override configuration dictionary

    Returns:
        Merged configuration dictionary
    """
    merged = base.copy()

    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            merged[key] = merge_configurations(merged[key], value)
        else:
            # Override or add new key
            merged[key] = value

    return merged


def validate_required_fields(
    data: Dict[str, Any], required_fields: List[str]
) -> List[str]:
    """Validate that required fields are present in data.

    Args:
        data: Data dictionary to validate
        required_fields: List of required field names

    Returns:
        List of missing field names
    """
    missing = []
    for field in required_fields:
        if "." in field:
            # Handle nested fields
            if safe_get(data, field) is None:
                missing.append(field)
        else:
            # Handle top-level fields
            if field not in data or data[field] is None:
                missing.append(field)

    return missing


def truncate_description(
    description: Optional[str], max_length: int = 500
) -> Optional[str]:
    """Truncate description to maximum length.

    Args:
        description: Description text to truncate
        max_length: Maximum allowed length

    Returns:
        Truncated description or None if input was None
    """
    if not description:
        return description

    if len(description) <= max_length:
        return description

    # Truncate and add ellipsis
    return description[: max_length - 3] + "..."
