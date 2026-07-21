"""Type definitions for CLI arguments."""

from __future__ import annotations

from typing import Any, List


class Argument:
    """Description of an argument for a command."""

    def __init__(
        self,
        *flags: str,
        type: type = str,
        default: Any = None,
        help: str = "",
        required: bool = False,
        choices: List[Any] | None = None,
        action: str | None = None,
    ):
        self.flags = flags
        self.type = type
        self.default = default
        self.help = help
        self.required = required
        self.choices = choices
        self.action = action


class ArgumentDef:
    """Definition of a command-line argument or option."""

    __slots__ = (
        "name",
        "flags",
        "help_flags",
        "default",
        "type",
        "help",
        "action",
        "required",
        "is_bool",
        "negated_flag",
    )

    def __init__(
        self, name: str, flags: List[str], help_flags: List[str] | None = None, **kwargs
    ):
        self.name = name
        self.flags = flags
        self.help_flags = help_flags if help_flags is not None else flags
        self.default = kwargs.get("default")
        self.type = kwargs.get("type", str)
        self.help = kwargs.get("help", "")
        self.action = kwargs.get("action")
        self.required = kwargs.get("required", False)
        self.is_bool = kwargs.get("is_bool", False)
        self.negated_flag = kwargs.get("negated_flag")
