"""Compatibility helpers for different Python versions."""

from __future__ import annotations

from types import UnionType
from typing import Union


def is_union_origin(origin) -> bool:
    """Check if origin is Union (typing.Union or types.UnionType)."""
    return origin in (Union, UnionType)
