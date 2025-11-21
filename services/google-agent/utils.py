"""Utility functions for Google agent."""

from typing import Any


def find_data_part(key: str, data_parts: list[dict[str, Any]]) -> Any | None:
    """Extract value by key from data parts.

    Args:
        key: Key to search for
        data_parts: List of data part dictionaries

    Returns:
        Value for key if found, None otherwise
    """
    for data_part in data_parts:
        if key in data_part:
            return data_part[key]
    return None


def parse_request_parts(message) -> tuple[list[str], list[dict]]:
    """Parse A2A message into text and data parts.

    Args:
        message: A2A Message object

    Returns:
        Tuple of (text_parts, data_parts)
    """
    text_parts = []
    data_parts = []

    if not message:
        return text_parts, data_parts

    for part in message.parts:
        if part.root.kind == "text":
            text_parts.append(part.root.text)
        elif part.root.kind == "data":
            data_parts.append(part.root.data)

    return text_parts, data_parts
