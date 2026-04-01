"""claudexml — Pydantic-like XML parser for Claude's XML output."""

from claudexml.exceptions import ClaudeXMLError, ParseError, TagNotFoundError, ValidationError
from claudexml.extract import extract_tags
from claudexml.integration import parse_response
from claudexml.model import XMLModel, XMLTag
from claudexml.stream import XMLStreamParser
from claudexml.validators import field_validator, register_coercer

__version__ = "1.0.0"

__all__ = [
    "ClaudeXMLError",
    "ParseError",
    "TagNotFoundError",
    "ValidationError",
    "XMLModel",
    "XMLStreamParser",
    "XMLTag",
    "extract_tags",
    "field_validator",
    "parse_response",
    "register_coercer",
]
