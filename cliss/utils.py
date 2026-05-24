"""Internal utilities for type handling."""

from __future__ import annotations

import inspect
from types import UnionType
from typing import Any, Union, get_args, get_origin

_UNION_ORIGINS = frozenset({Union, UnionType})
_NONE_TYPE = type(None)


def _is_union(origin) -> bool:
    """Check if origin is Union."""
    return origin in _UNION_ORIGINS


def get_type_from_annotation(annotation, default: Any = None) -> type:
    """Extract a usable type from a type annotation."""
    if isinstance(annotation, str) or annotation is inspect.Parameter.empty:
        return type(default) if default is not inspect.Parameter.empty else str

    origin = get_origin(annotation)
    if origin is None or not _is_union(origin):
        return annotation if isinstance(annotation, type) else str

    non_none = [a for a in get_args(annotation) if a is not _NONE_TYPE]
    return (
        non_none[0]
        if non_none
        else (type(default) if default is not inspect.Parameter.empty else str)
    )


def is_bool_type(param: inspect.Parameter) -> bool:
    """Check if a function parameter represents a boolean flag."""
    annotation = param.annotation

    if isinstance(annotation, str):
        return annotation in {
            "bool",
            "Optional[bool]",
            "Union[bool, None]",
            "Union[bool, NoneType]",
        }

    if annotation is bool:
        return True

    if annotation is inspect.Parameter.empty:
        return isinstance(param.default, bool)

    origin = get_origin(annotation)
    if origin is not None and _is_union(origin):
        non_none = [a for a in get_args(annotation) if a is not _NONE_TYPE]
        return len(non_none) == 1 and non_none[0] is bool

    return False
