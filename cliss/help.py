"""Help system for CLI"""

from __future__ import annotations

import re
import shutil
from functools import lru_cache
from typing import TYPE_CHECKING, Dict, List

from .colors import BOLD_CYAN, BOLD_GREEN, WHITE, styled

if TYPE_CHECKING:
    from .cli import CLI, ArgumentDef


class HelpTheme:
    """Theme configuration for help output in Cargo style."""

    __slots__ = ("usage", "header", "option_string", "metavar", "description")

    def __init__(
        self,
        usage: str = BOLD_CYAN,
        header: str = BOLD_GREEN,
        option_string: str = BOLD_CYAN,
        metavar: str = BOLD_CYAN,
        description: str = WHITE,
    ):
        self.usage = usage
        self.header = header
        self.option_string = option_string
        self.metavar = metavar
        self.description = description

    def apply_header(self, text: str) -> str:
        """Apply header style (bold green for cargo-like headers)."""
        return styled(text, self.header)


class HelpFormatter:
    """Standalone help formatter"""

    _ANSI_RE = re.compile(r"\033\[[0-9;]*m")

    def __init__(
        self,
        prog: str,
        indent_increment: int = 2,
        max_help_position: int = 27,
        width: int | None = None,
    ):
        self.prog = prog
        self.indent_increment = indent_increment
        self.max_help_position = max_help_position
        self.width = width or shutil.get_terminal_size().columns
        self._theme: HelpTheme | None = None

    def set_theme(self, theme: HelpTheme) -> None:
        self._theme = theme

    @staticmethod
    @lru_cache(1024)
    def _visible_len(text: str) -> int:
        """Return visible length of string without ANSI codes."""
        if "\033[" not in text:
            return len(text)
        return len(HelpFormatter._ANSI_RE.sub("", text))

    def _wrap_text(self, text: str, indent: int = 0) -> List[str]:
        """Wrap text to terminal width with indent."""
        prefix = " " * indent
        max_width = self.width - indent
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip() if current_line else word
            if self._visible_len(test_line) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(prefix + current_line)
                current_line = word

        if current_line:
            lines.append(prefix + current_line)

        return lines or [prefix]

    def format_help(
        self,
        description: str | None,
        usage: str,
        global_args: List["ArgumentDef"],
        commands: Dict[str, str],
        command_args: List["ArgumentDef"] | None = None,
    ) -> str:
        """Format complete help text."""
        theme = self._theme
        lines = []

        # Description
        if description:
            if theme:
                lines.append(styled(description, theme.description))
            else:
                lines.append(description)
            lines.append("")

        # Usage
        if theme:
            lines.append(f"{theme.apply_header('Usage:')} {styled(usage, theme.usage)}")
        else:
            lines.append(f"Usage: {usage}")
        lines.append("")

        # Global options
        if global_args:
            if theme:
                lines.append(theme.apply_header("Options:"))
            else:
                lines.append("Options:")
            lines.extend(self._format_arguments(global_args))
            lines.append("")

        # Commands
        if commands:
            if theme:
                lines.append(theme.apply_header("Commands:"))
            else:
                lines.append("Commands:")
            lines.extend(self._format_commands(commands))
            lines.append("")

        # Command-specific arguments
        if command_args:
            if theme:
                lines.append(theme.apply_header("Arguments:"))
            else:
                lines.append("Arguments:")
            lines.extend(self._format_arguments(command_args))

        return "\n".join(lines)

    def format_command_help(
        self,
        command_name: str,
        description: str | None,
        args: List["ArgumentDef"],
    ) -> str:
        """Format help for a specific command."""
        theme = self._theme
        lines = []

        # Description
        if description:
            if theme:
                lines.append(styled(description, theme.description))
            else:
                lines.append(description)
            lines.append("")

        # Usage
        usage = self._build_command_usage(command_name, args)
        if theme:
            lines.append(f"{theme.apply_header('Usage:')} {styled(usage, theme.usage)}")
        else:
            lines.append(f"Usage: {usage}")
        lines.append("")

        # Arguments
        if args:
            if theme:
                lines.append(theme.apply_header("Arguments:"))
            else:
                lines.append("Arguments:")
            lines.extend(self._format_arguments(args))

        return "\n".join(lines)

    def _format_arguments(self, args: List["ArgumentDef"]) -> List[str]:
        """Format a list of argument definitions."""
        theme = self._theme
        lines = []
        indent = "  "

        for arg in args:
            # Build invocation string
            flags = ", ".join(arg.flags)

            if arg.required or not arg.flags[0].startswith("-"):
                # Positional
                invocation = f"<{arg.name}>"
            else:
                invocation = flags

            if theme:
                styled_invocation = styled(invocation, theme.option_string)
            else:
                styled_invocation = invocation

            # Calculate padding
            inv_visible_len = self._visible_len(styled_invocation)
            padding = max(2, self.max_help_position - inv_visible_len)

            # Help text
            help_parts = []
            if arg.help:
                help_parts.append(arg.help)

            help_text = " ".join(help_parts)

            # Wrap help text if needed
            if help_text:
                wrapped = self._wrap_text(
                    help_text,
                    indent=self.max_help_position + 2,
                )
                if wrapped:
                    lines.append(
                        f"{indent}{styled_invocation}{' ' * padding}{wrapped[0].strip()}"
                    )
                    for line in wrapped[1:]:
                        lines.append(line)
                else:
                    lines.append(f"{indent}{styled_invocation}")
            else:
                lines.append(f"{indent}{styled_invocation}")

        return lines

    def _format_commands(self, commands: Dict[str, str]) -> List[str]:
        """Format list of commands."""
        theme = self._theme
        lines = []
        indent = "  "

        for cmd_name, cmd_desc in sorted(commands.items()):
            # Display only the short name, not full group:command
            display_name = cmd_name.split(":")[-1]

            if theme:
                styled_name = styled(display_name, theme.option_string)
            else:
                styled_name = display_name

            name_visible_len = self._visible_len(styled_name)
            padding = max(2, self.max_help_position - name_visible_len)

            if cmd_desc:
                # Use first line of description
                short_desc = cmd_desc.split("\n")[0]
                wrapped = self._wrap_text(
                    short_desc,
                    indent=self.max_help_position + 2,
                )
                if wrapped:
                    lines.append(
                        f"{indent}{styled_name}{' ' * padding}{wrapped[0].strip()}"
                    )
                    for line in wrapped[1:]:
                        lines.append(line)
                else:
                    lines.append(f"{indent}{styled_name}")
            else:
                lines.append(f"{indent}{styled_name}")

        return lines

    def _build_command_usage(self, command_name: str, args: List["ArgumentDef"]) -> str:
        """Build usage string for a command."""
        parts = [self.prog, command_name]

        for arg in args:
            if arg.required:
                parts.append(f"<{arg.name}>")
            else:
                if arg.flags and arg.flags[0].startswith("-"):
                    flag = arg.flags[0]
                    parts.append(f"[{flag}]")
                else:
                    parts.append(f"[<{arg.name}>]")

        return " ".join(parts)


class Help:
    """Help system for CLI — manages help text generation and display."""

    __slots__ = (
        "cli",
        "usage",
        "theme",
        "max_help_position",
        "width",
        "_commands_help",
    )

    def __init__(
        self,
        cli: "CLI",
        usage: str,
        theme: HelpTheme | None = None,
        max_help_position: int = 27,
        width: int | None = None,
    ):
        self.cli = cli
        self.usage = usage
        self.theme = theme or HelpTheme()
        self.max_help_position = max_help_position
        self.width = width
        self._commands_help: Dict[str, dict] = {}

    def _create_formatter(self) -> HelpFormatter:
        """Create and configure a help formatter."""
        formatter = HelpFormatter(
            self.cli.name or "cli",
            max_help_position=self.max_help_position,
            width=self.width,
        )
        formatter.set_theme(self.theme)
        return formatter

    def register_command_help(
        self,
        command_name: str,
        help_text: str | None = None,
        usage: str | None = None,
        examples: List[str] | None = None,
    ) -> None:
        """Register custom help information for a command."""
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
        """Format main help text."""
        formatter = self._create_formatter()

        return formatter.format_help(
            description=description,
            usage=self.usage,
            global_args=global_args,
            commands=commands,
        )

    def format_command_help(
        self,
        command_name: str,
        description: str | None,
        args: List["ArgumentDef"],
    ) -> str:
        """Format help text for a specific command."""
        custom = self._commands_help.get(command_name, {})
        custom_help = custom.get("help", description)
        custom_usage = custom.get("usage")

        formatter = self._create_formatter()

        help_text = formatter.format_command_help(
            command_name=command_name,
            description=custom_help,
            args=args,
        )

        # Override usage if custom
        if custom_usage:
            theme = self.theme
            usage_line = (
                f"{theme.apply_header('Usage:')} {styled(custom_usage, theme.usage)}"
            )
            # Replace the usage line
            lines = help_text.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("Usage:" if not theme else ""):
                    lines[i] = usage_line
                    break
            help_text = "\n".join(lines)

        # Add examples
        examples = custom.get("examples")
        if examples:
            help_text += f"\n{self.theme.apply_header('EXAMPLES:')}\n"
            help_text += "".join(f"  {styled(e, WHITE)}\n" for e in examples)

        return help_text

    def get_command_list(self) -> List[str]:
        """Get a list of all registered commands."""
        return list(self.cli._commands.keys())

    def add_examples(self, command_name: str, examples: List[str]) -> None:
        """Add usage examples for a command."""
        self._commands_help.setdefault(command_name, {})["examples"] = examples

    def add_long_description(self, command_name: str, description: str) -> None:
        """Add a long description for a command."""
        self._commands_help.setdefault(command_name, {})["help"] = description
