"""Internal utilities for type handling."""

from __future__ import annotations

import inspect
from typing import Any, get_args, get_origin

from ._compat import is_union_origin


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
    if origin is not None and is_union_origin(origin):
        non_none = [a for a in get_args(annotation) if a is not type(None)]
        if non_none:
            return non_none[0]
        return type(default) if default is not inspect.Parameter.empty else str

    return annotation if isinstance(annotation, type) else str


def is_bool_type(param: inspect.Parameter) -> bool:
    """
    Check if a function parameter represents a boolean flag.

    Recognises: bool, Optional[bool], Union[bool, None], and unannotated params
    with boolean default values.
    """
    annotation = param.annotation

    if isinstance(annotation, str):
        return annotation in (
            "bool",
            "Optional[bool]",
            "Union[bool, None]",
            "Union[bool, NoneType]",
        )

    origin = get_origin(annotation)
    if origin is not None and is_union_origin(origin):
        non_none = [a for a in get_args(annotation) if a is not type(None)]
        return len(non_none) == 1 and non_none[0] is bool

    if annotation is bool:
        return True
    if isinstance(param.default, bool) and annotation is inspect.Parameter.empty:
        return True
    return False
