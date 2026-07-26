"""Type definitions for CLI arguments."""

from __future__ import annotations

from typing import Any


class Argument:
    """Description of an argument for a command."""

    def __init__(
        self,
        *flags: str,
        type: type = str,
        default: Any = None,
        help: str = "",
        required: bool = False,
        choices: list[Any] | None = None,
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
        "action",
        "default",
        "flags",
        "help",
        "help_flags",
        "is_bool",
        "name",
        "negated_flag",
        "required",
        "type",
    )

    def __init__(
        self, name: str, flags: list[str], help_flags: list[str] | None = None, **kwargs
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
