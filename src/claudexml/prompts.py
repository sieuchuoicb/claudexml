"""Prompt helpers for generating XML schema instructions for Claude."""

from __future__ import annotations

from typing import get_args, get_origin

# Map Python types to human-readable names
_TYPE_NAMES: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


def _type_display_name(field_type: type) -> str:
    """Get a human-readable name for a type."""
    origin = get_origin(field_type)
    args = get_args(field_type)

    # Handle Optional (X | None)
    if origin is type(int | str):  # UnionType
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _type_display_name(non_none[0])

    try:
        from typing import Union

        if origin is Union:
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                return _type_display_name(non_none[0])
    except ImportError:
        pass

    # Handle list[X]
    if origin is list:
        if args:
            return f"list of {_type_display_name(args[0])}"
        return "list"

    # Check known type names
    if field_type in _TYPE_NAMES:
        return _TYPE_NAMES[field_type]

    # Fallback to class name
    if hasattr(field_type, "__name__"):
        return field_type.__name__

    return str(field_type)


def generate_xml_prompt(model_cls: type) -> str:
    """Generate XML schema instructions for use in Claude prompts.

    Introspects an XMLModel subclass and produces human-readable
    instructions describing the expected XML structure.

    Args:
        model_cls: An XMLModel subclass.

    Returns:
        A string suitable for inclusion in a system or user prompt.
    """
    from claudexml.model import _MISSING

    fields = model_cls._get_fields()  # type: ignore[attr-defined]

    lines = ["Respond using the following XML structure:\n"]

    for field_name, (tag_descriptor, field_type) in fields.items():
        type_name = _type_display_name(field_type)

        if tag_descriptor.attribute is not None:
            tag_display = f'<{tag_descriptor.tag} {tag_descriptor.attribute}="...">'
        else:
            tag_display = f"<{tag_descriptor.tag}>"

        if tag_descriptor.default is _MISSING:
            req = "required"
        elif tag_descriptor.default is None:
            req = "optional"
        else:
            req = f"optional, default: {tag_descriptor.default!r}"

        lines.append(f"- {tag_display}: {type_name} ({req})")

    return "\n".join(lines)
