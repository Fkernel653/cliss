"""Help system for CLI"""

from __future__ import annotations

import os
import re
import shutil
from functools import lru_cache
from typing import TYPE_CHECKING, Dict, List

from .colors import BOLD_CYAN, BOLD_GREEN, WHITE, styled

if TYPE_CHECKING:
    from .cli import CLI, ArgumentDef


class HelpTheme:
    __slots__ = (
        "usage",
        "header",
        "option_string",
        "metavar",
        "description",
        "_colour",
    )

    def __init__(
        self,
        usage: str = BOLD_CYAN,
        header: str = BOLD_GREEN,
        option_string: str = BOLD_CYAN,
        metavar: str = BOLD_CYAN,
        description: str = WHITE,
        colour: bool = True,
    ):
        self.usage = usage
        self.header = header
        self.option_string = option_string
        self.metavar = metavar
        self.description = description
        self._colour = colour

    @property
    def colour(self) -> bool:
        return self._colour

    @colour.setter
    def colour(self, value: bool) -> None:
        self._colour = value

    def apply_style(self, text: str, style: str) -> str:
        return styled(text, style) if self._colour else text

    def apply_header(self, text: str) -> str:
        return self.apply_style(text, self.header)

    def apply_usage(self, text: str) -> str:
        return self.apply_style(text, self.usage)

    def apply_option(self, text: str) -> str:
        return self.apply_style(text, self.option_string)

    def apply_metavar(self, text: str) -> str:
        return self.apply_style(text, self.metavar)

    def apply_description(self, text: str) -> str:
        return self.apply_style(text, self.description)


class HelpFormatter:
    _ANSI_RE = re.compile(r"\033\[[0-9;]*m")

    def __init__(
        self,
        prog: str,
        indent_increment: int = 2,
        max_help_position: int = 27,
        width: int | None = None,
        colour: bool = True,
    ):
        self.prog = prog
        self.indent_increment = indent_increment
        self.max_help_position = max_help_position
        self.width = width or shutil.get_terminal_size().columns
        self._theme: HelpTheme | None = None
        self._colour = colour

    @property
    def colour(self) -> bool:
        return self._colour

    @colour.setter
    def colour(self, value: bool) -> None:
        self._colour = value
        if self._theme:
            self._theme.colour = value

    def set_theme(self, theme: HelpTheme) -> None:
        self._theme = theme
        theme.colour = self._colour

    @staticmethod
    @lru_cache(1024)
    def _visible_len(text: str) -> int:
        return (
            len(HelpFormatter._ANSI_RE.sub("", text)) if "\033[" in text else len(text)
        )

    def _wrap_text(self, text: str, indent: int = 0) -> List[str]:
        prefix = " " * indent
        max_width = self.width - indent
        lines, current = [], ""

        for word in text.split():
            test = f"{current} {word}".strip() if current else word
            if self._visible_len(test) <= max_width:
                current = test
            else:
                if current:
                    lines.append(prefix + current)
                current = word

        if current:
            lines.append(prefix + current)
        return lines or [prefix]

    def format_help(
        self,
        description: str | None,
        usage: str,
        global_args: List["ArgumentDef"],
        commands: Dict[str, str],
        command_args: List["ArgumentDef"] | None = None,
    ) -> str:
        t = self._theme
        lines = []

        if description:
            lines.extend([(t.apply_description(description) if t else description), ""])

        lines.append(
            f"{t.apply_header('Usage:') if t else 'Usage:'} {t.apply_usage(usage) if t else usage}"
        )
        lines.append("")

        for title, args in [
            ("Options:", global_args),
            ("Commands:", commands),
            ("Arguments:", command_args),
        ]:
            if args:
                lines.append(t.apply_header(title) if t else title)
                lines.extend(
                    self._format_arguments(args)
                    if title != "Commands:"
                    else self._format_commands(commands)
                )
                lines.append("")

        return "\n".join(lines)

    def format_command_help(
        self, command_name: str, description: str | None, args: List["ArgumentDef"]
    ) -> str:
        t = self._theme
        lines = []

        if description:
            lines.extend([(t.apply_description(description) if t else description), ""])

        usage = self._build_command_usage(command_name, args)
        lines.append(
            f"{t.apply_header('Usage:') if t else 'Usage:'} {t.apply_usage(usage) if t else usage}"
        )
        lines.append("")

        if args:
            lines.append(t.apply_header("Arguments:") if t else "Arguments:")
            lines.extend(self._format_arguments(args))

        return "\n".join(lines)

    def _format_arguments(self, args: List["ArgumentDef"]) -> List[str]:
        t, lines = self._theme, []
        indent, padding_base = "  ", self.max_help_position + 2

        for arg in args:
            flags = ", ".join(arg.flags)
            invocation = (
                f"<{arg.name}>"
                if (arg.required or not arg.flags[0].startswith("-"))
                else flags
            )
            styled_inv = t.apply_option(invocation) if t else invocation
            padding = max(2, self.max_help_position - self._visible_len(styled_inv))

            if arg.help:
                wrapped = self._wrap_text(arg.help, indent=padding_base)
                lines.append(f"{indent}{styled_inv}{' ' * padding}{wrapped[0].strip()}")
                lines.extend(wrapped[1:])
            else:
                lines.append(f"{indent}{styled_inv}")

        return lines

    def _format_commands(self, commands: Dict[str, str]) -> List[str]:
        t, lines = self._theme, []
        indent, padding_base = "  ", self.max_help_position + 2

        for cmd_name, cmd_desc in sorted(commands.items()):
            styled_name = (
                t.apply_option(cmd_name.split(":")[-1])
                if t
                else cmd_name.split(":")[-1]
            )
            padding = max(2, self.max_help_position - self._visible_len(styled_name))

            if cmd_desc:
                wrapped = self._wrap_text(cmd_desc.split("\n")[0], indent=padding_base)
                lines.append(
                    f"{indent}{styled_name}{' ' * padding}{wrapped[0].strip()}"
                )
                lines.extend(wrapped[1:])
            else:
                lines.append(f"{indent}{styled_name}")

        return lines

    def _build_command_usage(self, command_name: str, args: List["ArgumentDef"]) -> str:
        parts = [self.prog, command_name]
        for arg in args:
            if arg.required:
                parts.append(f"<{arg.name}>")
            elif arg.flags and arg.flags[0].startswith("-"):
                parts.append(f"[{arg.flags[0]}]")
            else:
                parts.append(f"[<{arg.name}>]")
        return " ".join(parts)


class Help:
    __slots__ = (
        "cli",
        "usage",
        "theme",
        "max_help_position",
        "width",
        "_commands_help",
        "_colour",
    )

    def __init__(
        self,
        cli: "CLI",
        usage: str,
        theme: HelpTheme | None = None,
        max_help_position: int = 27,
        width: int | None = None,
        colour: bool = True,
    ):
        self.cli = cli
        self.usage = usage
        self.max_help_position = max_help_position
        self.width = width
        self._commands_help: Dict[str, dict] = {}
        self._colour = colour if not os.environ.get("NO_COLOR", "").strip() else False
        self.theme = theme or HelpTheme(colour=self._colour)

    @property
    def colour(self) -> bool:
        return self._colour

    @colour.setter
    def colour(self, value: bool) -> None:
        self._colour = value
        if self.theme:
            self.theme.colour = value

    def _create_formatter(self) -> HelpFormatter:
        f = HelpFormatter(
            self.cli.name or "cli",
            max_help_position=self.max_help_position,
            width=self.width,
            colour=self._colour,
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
