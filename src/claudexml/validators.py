"""Field validators and type coercion for claudexml."""

from __future__ import annotations

from typing import Any, Callable, TypeVar, get_args, get_origin

from claudexml.exceptions import ValidationError

T = TypeVar("T")

# Registry for field validators: class -> field_name -> list of validator functions
_validator_registry: dict[int, dict[str, list[Callable[..., Any]]]] = {}

# Registry for custom type coercers: type -> coercer function
_coercer_registry: dict[type, Callable[..., Any]] = {}


def register_coercer(target_type: type) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a custom coercer for a type.

    Usage:
        @register_coercer(datetime)
        def parse_datetime(value: str) -> datetime:
            return datetime.fromisoformat(value)
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        _coercer_registry[target_type] = func
        return func

    return decorator


def field_validator(*fields: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to register a validator for one or more fields.

    Usage:
        class MyModel(XMLModel):
            score: float = XMLTag("score")

            @field_validator("score")
            def check_score(cls, v):
                if not 0 <= v <= 1:
                    raise ValueError("score must be between 0 and 1")
                return v
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Store field names on the function for later registration
        func._validator_fields = fields  # type: ignore[attr-defined]
        return func

    return decorator


def register_validators(cls: type) -> None:
    """Scan a class for @field_validator methods and register them."""
    cls_id = id(cls)
    _validator_registry[cls_id] = {}

    for attr_name, attr in cls.__dict__.items():
        if callable(attr) and hasattr(attr, "_validator_fields"):
            for field_name in attr._validator_fields:  # type: ignore[attr-defined]
                if field_name not in _validator_registry[cls_id]:
                    _validator_registry[cls_id][field_name] = []
                _validator_registry[cls_id][field_name].append(attr)


def run_validators(cls: type, field_name: str, value: Any) -> Any:
    """Run all registered validators for a field."""
    cls_id = id(cls)
    validators = _validator_registry.get(cls_id, {}).get(field_name, [])
    for validator in validators:
        try:
            value = validator(cls, value)
        except (ValueError, TypeError) as e:
            raise ValidationError(field_name, str(e)) from e
    return value


def coerce_value(value: Any, target_type: type) -> Any:
    """Coerce a string value to the target type.

    Supports: str, int, float, bool, list, Optional, and nested XMLModel.
    """
    if value is None:
        return None

    origin = get_origin(target_type)
    args = get_args(target_type)

    # Handle Optional (Union[X, None])
    if origin is type(int | str):  # UnionType
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            return coerce_value(value, non_none_args[0])

    # Handle typing.Union for Optional
    try:
        from typing import Union
        if origin is Union:
            non_none_args = [a for a in args if a is not type(None)]
            if len(non_none_args) == 1:
                return coerce_value(value, non_none_args[0])
    except ImportError:
        pass

    # Handle list[X]
    if origin is list:
        if isinstance(value, list):
            if args:
                return [coerce_value(item, args[0]) for item in value]
            return value
        # Single item -> wrap in list
        if args:
            return [coerce_value(value, args[0])]
        return [value]

    # Check custom coercer registry
    if target_type in _coercer_registry:
        try:
            return _coercer_registry[target_type](value)
        except (ValueError, TypeError) as e:
            raise ValidationError(
                "", f"Custom coercer failed for {target_type.__name__}: {e}"
            ) from e

    # Handle XMLModel subclasses (nested models)
    from claudexml.model import XMLModel
    if isinstance(target_type, type) and issubclass(target_type, XMLModel):
        if isinstance(value, dict):
            return target_type._from_parsed(value)
        return value

    # Primitive types
    if target_type is str:
        return str(value) if value is not None else ""

    if target_type is int:
        try:
            return int(float(value)) if isinstance(value, str) else int(value)
        except (ValueError, TypeError) as e:
            raise ValidationError("", f"Cannot convert {value!r} to int") from e

    if target_type is float:
        try:
            return float(value)
        except (ValueError, TypeError) as e:
            raise ValidationError("", f"Cannot convert {value!r} to float") from e

    if target_type is bool:
        if isinstance(value, str):
            if value.lower() in ("true", "1", "yes"):
                return True
            if value.lower() in ("false", "0", "no"):
                return False
            raise ValidationError("", f"Cannot convert {value!r} to bool")
        return bool(value)

    return value
