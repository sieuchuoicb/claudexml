"""Schema-free XML tag extraction utility."""

from __future__ import annotations

from typing import Any

from claudexml.parser import parse_xml_string


def extract_tags(xml_string: str) -> dict[str, Any]:
    """Extract all XML tags from a string without a schema.

    This is the quick-and-dirty way to get data out of Claude's
    XML output without defining an XMLModel.

    Args:
        xml_string: Raw XML string from Claude's output.

    Returns:
        Dictionary mapping tag names to their string content.

    Example:
        >>> tags = extract_tags("<thinking>Let me analyze...</thinking><answer>42</answer>")
        >>> tags["thinking"]
        'Let me analyze...'
        >>> tags["answer"]
        '42'
    """
    return parse_xml_string(xml_string)
