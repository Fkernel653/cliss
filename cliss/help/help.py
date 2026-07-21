"""Help system for CLI."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Dict, List

from .formatter import HelpFormatter
from .theme import HelpTheme

if TYPE_CHECKING:
    from .._types.definitions import ArgumentDef
    from ..core.cli import Cliss


class Help:
    """Main help system manager."""

    __slots__ = (
        "cli",
        "usage",
        "theme",
        "max_help_position",
        "width",
        "_commands_help",
        "_color",
    )

    def __init__(
        self,
        cli: "Cliss",
        usage: str,
        theme: HelpTheme | None = None,
        max_help_position: int = 27,
        width: int | None = None,
        color: bool = True,
    ):
        self.cli = cli
        self.usage = usage
        self.max_help_position = max_help_position
        self.width = width
        self._commands_help: Dict[str, dict] = {}
        self._color = color if not os.environ.get("NO_COLOR", "").strip() else False
        self.theme = theme or HelpTheme(color=self._color)

    @property
    def color(self) -> bool:
        return self._color

    @color.setter
    def color(self, value: bool) -> None:
        self._color = value
        if self.theme:
            self.theme.color = value

    def _create_formatter(self) -> HelpFormatter:
        f = HelpFormatter(
            self.cli.name or "cli",
            max_help_position=self.max_help_position,
            width=self.width,
            color=self._color,
        )
        f.set_theme(self.theme)
        return f

    def register_command_help(
        self,
        command_name: str,
        help_text: str | None = None,
        usage: str | None = None,
        examples: List[str] | None = None,
    ) -> None:
        self._commands_help[command_name] = {
            "help": help_text,
            "usage": usage,
            "examples": examples or [],
        }

    def format_help(
        self,
        description: str | None,
        global_args: List["ArgumentDef"],
        commands: Dict[str, str],
    ) -> str:
        return self._create_formatter().format_help(
            description, self.usage, global_args, commands
        )

    def format_command_help(
        self, command_name: str, description: str | None, args: List["ArgumentDef"]
    ) -> str:
        custom = self._commands_help.get(command_name, {})
        formatter = self._create_formatter()
        help_text = formatter.format_command_help(
            command_name, custom.get("help", description), args
        )

        if custom.get("usage"):
            t = self.theme
            lines = help_text.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("Usage:"):
                    lines[i] = (
                        f"{t.apply_header('Usage:')} {t.apply_usage(custom['usage'])}"
                    )
                    break
            help_text = "\n".join(lines)

        if examples := custom.get("examples"):
            help_text += f"\n{self.theme.apply_header('EXAMPLES:')}\n" + "\n".join(
                f"  {self.theme.apply_description(e)}" for e in examples
            )

        return help_text

    def get_command_list(self) -> List[str]:
        return list(self.cli._commands.keys())

    def add_examples(self, command_name: str, examples: List[str]) -> None:
        self._commands_help.setdefault(command_name, {})["examples"] = examples

    def add_long_description(self, command_name: str, description: str) -> None:
        self._commands_help.setdefault(command_name, {})["help"] = description
