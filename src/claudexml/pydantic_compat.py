"""Optional Pydantic interop for claudexml."""

from __future__ import annotations

from typing import Any


def to_pydantic(instance: Any) -> Any:
    """Convert an XMLModel instance to a Pydantic BaseModel instance.

    Dynamically creates a Pydantic model class matching the XMLModel's
    fields and populates it with the instance's data.

    Args:
        instance: An XMLModel instance.

    Returns:
        A Pydantic BaseModel instance.

    Raises:
        ImportError: If pydantic is not installed.
    """
    try:
        from pydantic import create_model
    except ImportError:
        raise ImportError(
            "Pydantic is required for to_pydantic(). "
            "Install it with: pip install claudexml[pydantic]"
        ) from None

    from claudexml.model import XMLModel

    fields = instance._get_fields()
    pydantic_fields: dict[str, Any] = {}

    for field_name, (tag_descriptor, field_type) in fields.items():
        value = getattr(instance, field_name, None)

        # Recursively convert nested XMLModel instances
        if isinstance(value, XMLModel):
            value = to_pydantic(value)
            # Get the pydantic model class for the type annotation
            nested_pydantic = _make_pydantic_model(field_name, tag_descriptor, field_type)
            pydantic_fields[field_name] = (nested_pydantic, ...)
            continue
        elif isinstance(value, list):
            value = [to_pydantic(v) if isinstance(v, XMLModel) else v for v in value]

        from claudexml.model import _MISSING

        if tag_descriptor.default is _MISSING:
            pydantic_fields[field_name] = (field_type, ...)
        else:
            pydantic_fields[field_name] = (field_type, tag_descriptor.default)

    PydanticModel = create_model(
        instance.__class__.__name__, **pydantic_fields
    )

    data = instance.to_dict()
    return PydanticModel(**data)


def from_pydantic_model(pydantic_cls: type) -> type:
    """Create an XMLModel subclass from a Pydantic BaseModel class.

    Maps each Pydantic field to an XMLTag with the field name as the tag.

    Args:
        pydantic_cls: A Pydantic BaseModel class.

    Returns:
        A new XMLModel subclass.

    Raises:
        ImportError: If pydantic is not installed.
    """
    try:
        from pydantic import BaseModel
    except ImportError:
        raise ImportError(
            "Pydantic is required for from_pydantic_model(). "
            "Install it with: pip install claudexml[pydantic]"
        ) from None

    if not issubclass(pydantic_cls, BaseModel):
        raise TypeError(f"{pydantic_cls.__name__} is not a Pydantic BaseModel")

    from claudexml.model import XMLModel, XMLTag

    # Build namespace with XMLTag descriptors
    namespace: dict[str, Any] = {"__annotations__": {}}

    for field_name, field_info in pydantic_cls.model_fields.items():  # type: ignore[attr-defined]
        namespace["__annotations__"][field_name] = field_info.annotation

        if field_info.is_required():
            namespace[field_name] = XMLTag(field_name)
        else:
            namespace[field_name] = XMLTag(field_name, default=field_info.default)

    # Create the XMLModel subclass dynamically
    # XMLModelMeta will handle validator registration
    new_cls = type(pydantic_cls.__name__, (XMLModel,), namespace)
    return new_cls


def _make_pydantic_model(
    field_name: str, tag_descriptor: Any, field_type: type
) -> type:
    """Create a Pydantic model for a nested XMLModel type."""
    try:
        from pydantic import create_model
    except ImportError:
        raise ImportError(
            "Pydantic is required. Install it with: pip install claudexml[pydantic]"
        ) from None

    from claudexml.model import _MISSING, XMLModel

    if isinstance(field_type, type) and issubclass(field_type, XMLModel):
        fields = field_type._get_fields()
        pydantic_fields: dict[str, Any] = {}
        for fname, (tdesc, ftype) in fields.items():
            if tdesc.default is _MISSING:
                pydantic_fields[fname] = (ftype, ...)
            else:
                pydantic_fields[fname] = (ftype, tdesc.default)
        return create_model(field_type.__name__, **pydantic_fields)  # type: ignore[no-any-return]

    return field_type  # type: ignore[no-any-return]
