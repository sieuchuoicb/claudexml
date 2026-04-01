"""Integration with the Anthropic SDK."""

from __future__ import annotations

from typing import Any, TypeVar, cast

from claudexml.model import XMLModel

T = TypeVar("T", bound=XMLModel)


def parse_response(response: Any, model: type[T]) -> T:
    """Parse an Anthropic API response into an XMLModel instance.

    Works with the anthropic SDK's Message response object.
    Extracts text content and parses it with the given model.

    Args:
        response: An anthropic Message response object.
        model: The XMLModel subclass to parse into.

    Returns:
        A validated instance of the model.

    Example:
        from anthropic import Anthropic
        from claudexml import parse_response

        client = Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6-20250514",
            messages=[{"role": "user", "content": "..."}],
        )
        result = parse_response(response, MyModel)
    """
    text = _extract_text(response)
    return cast(T, model.from_xml(text))


def _extract_text(response: Any) -> str:
    """Extract text content from an Anthropic API response.

    Handles both the Message object and raw string input.
    """
    # If it's already a string, return as-is
    if isinstance(response, str):
        return response

    # Anthropic Message object
    if hasattr(response, "content"):
        content = response.content
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
                elif isinstance(block, dict) and "text" in block:
                    text_parts.append(block["text"])
            return "\n".join(text_parts)
        if isinstance(content, str):
            return content

    raise TypeError(
        f"Cannot extract text from {type(response).__name__}. "
        "Expected an Anthropic Message object or a string."
    )
