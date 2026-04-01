"""Streaming XML parser for incremental Claude responses."""

from __future__ import annotations

from typing import Any

from claudexml.exceptions import ParseError
from claudexml.model import _MISSING, XMLModel, _resolve_attribute, extract_from_parsed
from claudexml.parser import parse_xml_string
from claudexml.validators import coerce_value


class XMLStreamParser:
    """Incremental XML parser for streaming Claude responses.

    Parses XML progressively as Claude streams tokens, providing
    partial results before the full response is complete.

    Example:
        parser = XMLStreamParser(Analysis)
        for event in stream:
            parser.feed(event.text)
            partial = parser.partial()       # partially filled model
            if parser.is_complete():
                result = parser.result()     # fully validated model
    """

    def __init__(self, model: type[XMLModel]) -> None:
        self._model = model
        self._buffer = ""
        self._fields = model._get_fields()
        self._parsed: dict[str, Any] = {}

    def feed(self, text: str) -> None:
        """Append new text to the buffer and re-parse.

        Args:
            text: New text chunk from the stream.
        """
        if not text:
            return
        self._buffer += text
        self._parsed = parse_xml_string(self._buffer)

    def partial(self) -> XMLModel:
        """Return a partially filled model instance.

        Fields that haven't been found yet get their default value
        or None. Validators are NOT run — this is best-effort for
        UI display during streaming.

        Returns:
            A partially filled model instance.
        """
        kwargs: dict[str, Any] = {}

        for field_name, (tag_descriptor, field_type) in self._fields.items():
            raw_value = extract_from_parsed(self._parsed, tag_descriptor.tag)
            raw_value = _resolve_attribute(raw_value, tag_descriptor)

            if raw_value is not None:
                try:
                    kwargs[field_name] = coerce_value(raw_value, field_type)
                except Exception:
                    kwargs[field_name] = raw_value  # best effort
            else:
                if tag_descriptor.default is not _MISSING:
                    kwargs[field_name] = tag_descriptor.default
                else:
                    kwargs[field_name] = None

        return self._model(**kwargs)

    def is_complete(self) -> bool:
        """Check if all required fields have been found.

        Returns:
            True if every required field (no default) has a value.
        """
        for _field_name, (tag_descriptor, _field_type) in self._fields.items():
            if tag_descriptor.default is _MISSING:
                raw = extract_from_parsed(self._parsed, tag_descriptor.tag)
                raw = _resolve_attribute(raw, tag_descriptor)
                if raw is None:
                    return False
        return True

    def result(self) -> XMLModel:
        """Return a fully validated model instance.

        Runs all type coercion and validators. Raises if the stream
        is not yet complete.

        Returns:
            A fully validated model instance.

        Raises:
            ParseError: If required fields are still missing.
        """
        if not self.is_complete():
            raise ParseError(
                "Stream is not complete: missing required fields", self._buffer
            )
        return self._model._from_parsed(self._parsed)

    def reset(self) -> None:
        """Clear the buffer and parsed state."""
        self._buffer = ""
        self._parsed = {}
