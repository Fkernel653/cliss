"""Help formatter for CLI."""

from __future__ import annotations

import re
import shutil
from functools import lru_cache
from typing import TYPE_CHECKING, Dict, List

from .theme import HelpTheme

if TYPE_CHECKING:
    from .._types.definitions import ArgumentDef


class HelpFormatter:
    """Format help text for CLI commands."""

    _ANSI_RE = re.compile(r"\033\[[0-9;]*m")

    def __init__(
        self,
        prog: str,
        indent_increment: int = 2,
        max_help_position: int = 27,
        width: int | None = None,
        color: bool = True,
    ):
        self.prog = prog
        self.indent_increment = indent_increment
        self.max_help_position = max_help_position
        self.width = width or shutil.get_terminal_size().columns
        self._theme: HelpTheme | None = None
        self._color = color

    @property
    def color(self) -> bool:
        return self._color

    @color.setter
    def color(self, value: bool) -> None:
        self._color = value
        if self._theme:
            self._theme.color = value

    def set_theme(self, theme: HelpTheme) -> None:
        self._theme = theme
        theme.color = self._color

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
        global_args: List[ArgumentDef],
        commands: Dict[str, str],
        command_args: List[ArgumentDef] | None = None,
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
        self, command_name: str, description: str | None, args: List[ArgumentDef]
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

    def _format_arguments(self, args: List[ArgumentDef]) -> List[str]:
        t, lines = self._theme, []
        indent, padding_base = "  ", self.max_help_position + 2

        for arg in args:
            display_flags = getattr(arg, "help_flags", arg.flags)

            if display_flags and display_flags[0].startswith("-"):
                invocation = ", ".join(display_flags)
            else:
                invocation = f"<{arg.name}>"

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

    def _build_command_usage(self, command_name: str, args: List[ArgumentDef]) -> str:
        parts = [self.prog, command_name]
        for arg in args:
            display_flags = getattr(arg, "help_flags", arg.flags)

            if arg.required:
                if display_flags and display_flags[0].startswith("-"):
                    if len(display_flags) > 1:
                        parts.append(f"( {' | '.join(display_flags)} )")
                    else:
                        parts.append(display_flags[0])
                else:
                    parts.append(f"<{arg.name}>")
            else:
                if display_flags and display_flags[0].startswith("-"):
                    if len(display_flags) > 1:
                        parts.append(f"[ {' | '.join(display_flags)} ]")
                    else:
                        parts.append(f"[{display_flags[0]}]")
                else:
                    parts.append(f"[<{arg.name}>]")
        return " ".join(parts)
