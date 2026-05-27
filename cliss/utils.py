"""Internal utilities for type handling."""

from __future__ import annotations

import inspect
from typing import Any


def get_type_from_annotation(annotation, default: Any = None) -> type:
    """Extract a usable type from a type annotation."""
    if annotation is inspect.Parameter.empty:
        return type(default) if default is not inspect.Parameter.empty else str

    if isinstance(annotation, str):
        return type(default) if default is not inspect.Parameter.empty else str

    if isinstance(annotation, type):
        return annotation

    origin = getattr(annotation, "__origin__", None)
    if origin is not None:
        import types
        import typing

        if origin is typing.Union or origin is types.UnionType:
            args = getattr(annotation, "__args__", ())
            none_type = type(None)
            non_none = [a for a in args if a is not none_type]
            if non_none:
                return non_none[0] if isinstance(non_none[0], type) else str

    return str


def is_bool_type(param: inspect.Parameter) -> bool:
    """Check if a function parameter represents a boolean flag."""
    annotation = param.annotation

    if annotation is inspect.Parameter.empty:
        return isinstance(param.default, bool)

    if isinstance(annotation, str):
        return annotation in {
            "bool",
            "Optional[bool]",
            "Union[bool, None]",
            "Union[bool, NoneType]",
        }

    if annotation is bool:
        return True

    origin = getattr(annotation, "__origin__", None)
    if origin is not None:
        import types
        import typing

        if origin is typing.Union or origin is types.UnionType:
            args = getattr(annotation, "__args__", ())
            none_type = type(None)
            non_none = [a for a in args if a is not none_type]
            return len(non_none) == 1 and non_none[0] is bool

    return False
