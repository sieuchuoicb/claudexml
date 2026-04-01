"""XML parsing logic for Claude's output.

Uses a fault-tolerant regex-based approach since Claude's XML output
is not always well-formed (unclosed tags, mixed content, etc.).
Falls back to xml.etree for well-formed XML with nested structures.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any


def parse_xml_string(xml_string: str) -> dict[str, Any]:
    """Parse an XML string into a dictionary of tag -> content.

    Tries xml.etree first for well-formed XML, falls back to
    regex-based extraction for fault tolerance.

    Args:
        xml_string: Raw XML string, possibly with surrounding text.

    Returns:
        Dictionary mapping tag names to their content.
    """
    # Try wrapping in a root element for etree parsing
    wrapped = f"<root>{xml_string}</root>"
    try:
        root = ET.fromstring(wrapped)
        return _etree_to_dict(root)
    except ET.ParseError:
        return _regex_parse(xml_string)


def _etree_to_dict(element: ET.Element) -> dict[str, Any]:
    """Convert an ElementTree element to a dictionary."""
    result: dict[str, Any] = {}

    for child in element:
        tag = child.tag
        children_dict = _etree_to_dict(child)

        if children_dict:
            # Has nested children
            value: Any = children_dict
            if child.attrib:
                value["_attrs"] = dict(child.attrib)
        else:
            # Leaf node — get text content
            text = (child.text or "").strip()
            if child.attrib:
                value = {"_text": text, "_attrs": dict(child.attrib)}
            else:
                value = text

        if tag in result:
            # Multiple tags with same name -> list
            existing = result[tag]
            if isinstance(existing, list):
                existing.append(value)
            else:
                result[tag] = [existing, value]
        else:
            result[tag] = value

    return result


_CDATA_RE = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.DOTALL)


def _strip_cdata(xml_string: str) -> str:
    """Replace CDATA sections with their raw content."""
    return _CDATA_RE.sub(r"\1", xml_string)


_ATTR_RE = re.compile(r"""(\w+)=["']([^"']*)["']""")


def _parse_attrs(attr_string: str) -> dict[str, str]:
    """Parse attribute string into a dictionary."""
    return dict(_ATTR_RE.findall(attr_string))


def _regex_parse(xml_string: str) -> dict[str, Any]:
    """Fault-tolerant regex-based XML parsing.

    Handles unclosed tags, partial output, and mixed content.
    """
    xml_string = _strip_cdata(xml_string)
    result: dict[str, Any] = {}
    pattern = re.compile(
        r"<(\w+)((?:\s+\w+=[\"'][^\"']*[\"'])*)>(.*?)</\1>",
        re.DOTALL,
    )

    for match in pattern.finditer(xml_string):
        tag = match.group(1)
        attr_string = match.group(2)
        content = match.group(3).strip()
        attrs = _parse_attrs(attr_string) if attr_string.strip() else {}

        # Check if content has nested tags
        if pattern.search(content):
            nested = _regex_parse(content)
            value: Any = nested if nested else content
            if attrs:
                value["_attrs"] = attrs
        else:
            if attrs:
                value = {"_text": content, "_attrs": attrs}
            else:
                value = content

        if tag in result:
            existing = result[tag]
            if isinstance(existing, list):
                existing.append(value)
            else:
                result[tag] = [existing, value]
        else:
            result[tag] = value

    if not result:
        # Try to find unclosed tags as last resort
        unclosed_pattern = re.compile(
            r"<(\w+)((?:\s+\w+=[\"'][^\"']*[\"'])*)>([^<]*)", re.DOTALL
        )
        for match in unclosed_pattern.finditer(xml_string):
            tag = match.group(1)
            attr_string = match.group(2)
            content = match.group(3).strip()
            if content and tag not in result:
                attrs = _parse_attrs(attr_string) if attr_string.strip() else {}
                if attrs:
                    result[tag] = {"_text": content, "_attrs": attrs}
                else:
                    result[tag] = content

    return result


def extract_tag(xml_string: str, tag_path: str) -> Any:
    """Extract a specific tag's content from XML.

    Supports simple paths like "thinking" or nested paths like "sources/source".

    Args:
        xml_string: Raw XML string.
        tag_path: Dot or slash separated path to the tag.

    Returns:
        The content of the tag, or None if not found.
    """
    parsed = parse_xml_string(xml_string)
    parts = tag_path.replace(".", "/").split("/")

    current: Any = parsed
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    return current
