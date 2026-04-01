"""Core XMLModel and XMLTag definitions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, get_type_hints

from claudexml.exceptions import TagNotFoundError
from claudexml.parser import parse_xml_string
from claudexml.validators import coerce_value, register_validators, run_validators

_MISSING = object()


@dataclass
class XMLTag:
    """Field descriptor for mapping an XML tag to a model field.

    Args:
        tag: XML tag name or path (e.g., "thinking" or "sources/source").
        default: Default value if the tag is not found. Use _MISSING for required fields.
    """

    tag: str
    default: Any = _MISSING
    attribute: str | None = None

    def __init__(
        self, tag: str, default: Any = _MISSING, attribute: str | None = None
    ) -> None:
        self.tag = tag
        self.default = default
        self.attribute = attribute


class XMLModelMeta(type):
    """Metaclass for XMLModel that registers validators and collects field info."""

    def __new__(
        mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any]
    ) -> XMLModelMeta:
        cls = super().__new__(mcs, name, bases, namespace)
        if name != "XMLModel":
            register_validators(cls)  # type: ignore[arg-type]
        return cls


class XMLModel(metaclass=XMLModelMeta):
    """Base class for XML schema models.

    Define fields with XMLTag descriptors and type annotations,
    then use from_xml() to parse Claude's XML output.

    Example:
        class Analysis(XMLModel):
            thinking: str = XMLTag("thinking")
            answer: str = XMLTag("answer")
            confidence: float = XMLTag("confidence")

        result = Analysis.from_xml(claude_response)
    """

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def _get_fields(cls) -> dict[str, tuple[XMLTag, type]]:
        """Get all XMLTag fields with their type annotations."""
        hints = get_type_hints(cls)
        fields: dict[str, tuple[XMLTag, type]] = {}

        for field_name, field_type in hints.items():
            tag_descriptor = getattr(cls, field_name, None)
            if isinstance(tag_descriptor, XMLTag):
                fields[field_name] = (tag_descriptor, field_type)

        return fields

    @classmethod
    def from_xml(cls, xml_string: str) -> "XMLModel":
        """Parse an XML string into a validated model instance.

        Args:
            xml_string: Raw XML string from Claude's output.

        Returns:
            A validated instance of this model.

        Raises:
            TagNotFoundError: If a required tag is missing.
            ValidationError: If a field fails validation.
        """
        parsed = parse_xml_string(xml_string)
        return cls._from_parsed(parsed)

    @classmethod
    def _from_parsed(cls, parsed: dict[str, Any]) -> "XMLModel":
        """Create an instance from an already-parsed dictionary."""
        fields = cls._get_fields()
        kwargs: dict[str, Any] = {}

        for field_name, (tag_descriptor, field_type) in fields.items():
            raw_value = extract_from_parsed(parsed, tag_descriptor.tag)
            raw_value = _resolve_attribute(raw_value, tag_descriptor)

            if raw_value is None:
                if tag_descriptor.default is _MISSING:
                    raise TagNotFoundError(tag_descriptor.tag)
                kwargs[field_name] = tag_descriptor.default
                continue

            # Coerce to target type
            value = coerce_value(raw_value, field_type)

            # Run validators
            value = run_validators(cls, field_name, value)

            kwargs[field_name] = value

        return cls(**kwargs)

    def __repr__(self) -> str:
        fields = self._get_fields()
        parts = []
        for field_name in fields:
            value = getattr(self, field_name, None)
            parts.append(f"{field_name}={value!r}")
        return f"{self.__class__.__name__}({', '.join(parts)})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        fields = self._get_fields()
        return all(
            getattr(self, f, None) == getattr(other, f, None) for f in fields
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the model to a dictionary."""
        fields = self._get_fields()
        result: dict[str, Any] = {}
        for field_name in fields:
            value = getattr(self, field_name, None)
            if isinstance(value, XMLModel):
                result[field_name] = value.to_dict()
            elif isinstance(value, list):
                result[field_name] = [
                    item.to_dict() if isinstance(item, XMLModel) else item
                    for item in value
                ]
            else:
                result[field_name] = value
        return result

    def to_json(self, indent: int | None = None) -> str:
        """Convert the model to a JSON string.

        Args:
            indent: Number of spaces for indentation. None for compact output.

        Returns:
            JSON string representation of the model.
        """
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def xml_prompt(cls) -> str:
        """Generate XML schema instructions for use in Claude prompts.

        Returns a string describing the expected XML structure that can
        be included in system or user prompts.
        """
        from claudexml.prompts import generate_xml_prompt

        return generate_xml_prompt(cls)

    def to_pydantic(self) -> Any:
        """Convert this model instance to a Pydantic BaseModel instance.

        Requires pydantic to be installed: pip install claudexml[pydantic]
        """
        from claudexml.pydantic_compat import to_pydantic

        return to_pydantic(self)

    @classmethod
    def from_pydantic_model(cls, pydantic_cls: type) -> type["XMLModel"]:
        """Create an XMLModel subclass from a Pydantic BaseModel class.

        Maps each Pydantic field to an XMLTag with the field name as the tag.
        Requires pydantic to be installed: pip install claudexml[pydantic]
        """
        from claudexml.pydantic_compat import from_pydantic_model

        return from_pydantic_model(pydantic_cls)


def _resolve_attribute(raw_value: Any, tag_descriptor: XMLTag) -> Any:
    """Resolve attribute vs text content from a parsed value.

    When a tag has attributes, the parsed value is a dict with
    "_text" and "_attrs" keys. This function extracts the right value
    based on the XMLTag descriptor.
    """
    if raw_value is None:
        return None
    if tag_descriptor.attribute is not None:
        # Field wants an attribute value
        if isinstance(raw_value, dict):
            return raw_value.get("_attrs", {}).get(tag_descriptor.attribute)
        # Tag exists but has no attributes — attribute not found
        return None
    if isinstance(raw_value, dict) and "_text" in raw_value:
        # Tag has attributes but field wants text content
        return raw_value["_text"]
    return raw_value


def extract_from_parsed(parsed: dict[str, Any], tag_path: str) -> Any:
    """Extract a value from a parsed dictionary using a tag path."""
    parts = tag_path.replace(".", "/").split("/")
    current: Any = parsed

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    return current
