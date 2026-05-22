"""Internal utilities for type handling."""

from __future__ import annotations

import inspect
from types import UnionType
from typing import Any, Union, get_args, get_origin

_UNION_ORIGINS = frozenset({Union, UnionType})
_BOOL_ANNOTATIONS = frozenset(
    {
        "bool",
        "Optional[bool]",
        "Union[bool, None]",
        "Union[bool, NoneType]",
    }
)
_NONE_TYPE = type(None)


def is_union_origin(origin) -> bool:
    """Check if origin is Union (typing.Union or types.UnionType)."""
    return origin in _UNION_ORIGINS


def get_type_from_annotation(annotation, default: Any = None) -> type:
    """
    Extract a usable type from a type annotation.

    Handles plain types, Optional[X], Union[X, None], and string annotations.
    Falls back to str if no type can be determined.
    """
    if annotation is inspect.Parameter.empty:
        return type(default) if default is not inspect.Parameter.empty else str

    if isinstance(annotation, str):
        return type(default) if default is not inspect.Parameter.empty else str

    origin = get_origin(annotation)

    if origin is None or not is_union_origin(origin):
        return annotation if isinstance(annotation, type) else str

    args = get_args(annotation)

    non_none = [a for a in args if a is not _NONE_TYPE]

    if non_none:
        return non_none[0]

    return type(default) if default is not inspect.Parameter.empty else str


def is_bool_type(param: inspect.Parameter) -> bool:
    """
    Check if a function parameter represents a boolean flag.

    Recognises: bool, Optional[bool], Union[bool, None], and unannotated params
    with boolean default values.
    """
    annotation = param.annotation

    if isinstance(annotation, str):
        return annotation in _BOOL_ANNOTATIONS

    if annotation is bool:
        return True

    if annotation is inspect.Parameter.empty:
        return isinstance(param.default, bool)

    origin = get_origin(annotation)
    if origin is not None and is_union_origin(origin):
        args = get_args(annotation)
        non_none = [a for a in args if a is not _NONE_TYPE]
        return len(non_none) == 1 and non_none[0] is bool

    return False
