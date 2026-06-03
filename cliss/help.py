"""Help system for CLI — extended argparse help formatting."""

from __future__ import annotations

import argparse
import re
import sys
from typing import TYPE_CHECKING, Dict, List, TextIO, TypedDict

from color_kiss import BOLD_CYAN, BOLD_GREEN, WHITE
from color_kiss.utils import styled

if TYPE_CHECKING:
    from .cli import CLI


class CommandHelpInfo(TypedDict, total=False):
    """TypedDict to store information about the command's help."""

    help: str | None
    usage: str | None
    examples: List[str]


class HelpTheme:
    """Theme configuration for help output in Cargo style."""

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


class HelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Extended help formatter with Cargo-style colour support."""

    _ANSI_RE = re.compile(r"\033\[[0-9;]*m")

    def __init__(
        self,
        prog: str,
        indent_increment: int = 2,
        max_help_position: int = 22,
        width: int | None = None,
    ):
        super().__init__(prog, indent_increment, max_help_position, width)
        self._help_theme: HelpTheme | None = None

    def set_theme(self, theme: HelpTheme) -> None:
        """Set the colour theme."""
        self._help_theme = theme

    @staticmethod
    def _visible_len(text: str) -> int:
        """Return visible length of string without ANSI codes."""
        return len(HelpFormatter._ANSI_RE.sub("", text))

    def _format_usage(self, usage, actions, groups, prefix):
        """Format usage line with positional arguments before optional [OPTIONS] block."""
        prefix = prefix or "Usage: "
        positional_actions = [a for a in actions if not a.option_strings]
        optional_actions = [a for a in actions if a.option_strings]

        if usage is None:
            parts = [self._prog]
            for action in positional_actions:
                parts.append(f"<{self._format_action_invocation(action)}>")
            if optional_actions:
                theme = self._help_theme
                parts.append(
                    styled("[OPTIONS]", theme.option_string) if theme else "[OPTIONS]"
                )
            usage = " ".join(parts)

        formatted = super()._format_usage(
            usage, positional_actions + optional_actions, groups, prefix
        )
        if not self._help_theme:
            return formatted

        lines = []
        for i, line in enumerate(formatted.split("\n")):
            if i == 0 and line.startswith("Usage:"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    lines.append(
                        f"{self._help_theme.apply_header('Usage:')} {styled(parts[1].strip(), self._help_theme.usage)}"
                    )
                else:
                    lines.append(self._help_theme.apply_header(line))
            elif line.strip():
                stripped = line.lstrip()
                indent = len(line) - len(stripped)
                lines.append(
                    f"{' ' * indent}{styled(stripped, self._help_theme.usage)}"
                )
            else:
                lines.append(line)
        return "\n".join(lines)

    def _format_action(self, action: argparse.Action) -> str:
        """Format a single action with styled invocation and aligned help text."""
        if isinstance(action, argparse._SubParsersAction):
            return "\n".join(
                self._format_action(a).rstrip("\n") for a in action._choices_actions
            )

        if action.help is None:
            return super()._format_action(action)

        invocation = self._format_action_invocation(action)
        theme = self._help_theme
        styled_invocation = (
            styled(invocation, theme.option_string) if theme else invocation
        )
        indent = min(self._visible_len(styled_invocation), self._max_help_position)
        help_text = self._expand_help(action)
        return f"  {styled_invocation}{' ' * (self._max_help_position - indent)}{help_text}\n"

    def _format_action_invocation(self, action: argparse.Action) -> str:
        """Return the invocation string for an action."""
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            (metavar,) = self._metavar_formatter(action, default)(1)
            return metavar
        if not self._help_theme:
            return ", ".join(action.option_strings)
        return ", ".join(
            styled(opt, self._help_theme.option_string) for opt in action.option_strings
        )

    def _metavar_formatter(self, action: argparse.Action, default_metavar: str):
        """Return a callable that formats metavar strings for the given action."""
        original = super()._metavar_formatter(action, default_metavar)
        if not self._help_theme:
            return original

        def coloured_formatter(size: int) -> tuple[str, ...]:
            return original(size)

        return coloured_formatter

    def start_section(self, heading: str | None) -> None:
        """Start a new help section with an optionally styled heading."""
        if heading and self._help_theme:
            heading = self._help_theme.apply_header(heading.capitalize())
        super().start_section(heading)


class Help:
    """Help system for CLI — manages help text generation and display."""

    def __init__(
        self,
        cli: "CLI",
        theme: HelpTheme | None = None,
        max_help_position: int = 22,
        width: int | None = None,
    ):
        self.cli = cli
        self.theme = theme or HelpTheme()
        self.max_help_position = max_help_position
        self.width = width
        self._commands_help: Dict[str, CommandHelpInfo] = {}

    def _create_formatter(self, parser: argparse.ArgumentParser) -> HelpFormatter:
        """Create and configure a help formatter."""
        formatter = HelpFormatter(
            parser.prog, max_help_position=self.max_help_position, width=self.width
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

    def format_help(self, parser: argparse.ArgumentParser) -> str:
        """Format help text for a parser with description on top."""
        formatter = self._create_formatter(parser)
        if parser.description:
            formatter.add_text(parser.description)
            formatter.add_text("")
        formatter.add_usage(
            parser.usage, parser._actions, parser._mutually_exclusive_groups
        )
        for group in parser._action_groups:
            formatter.start_section(group.title)
            formatter.add_text(group.description)
            formatter.add_arguments(group._group_actions)
            formatter.end_section()
        formatter.add_text(parser.epilog)
        return formatter.format_help()

    def format_command_help(
        self, command_name: str, parser: argparse.ArgumentParser
    ) -> str:
        """Format help text for a specific command."""
        custom = self._commands_help.get(command_name, {})
        custom_usage = custom.get("usage")
        custom_help = custom.get("help")

        original_description = parser.description if custom_help else None
        if custom_help:
            parser.description = custom_help

        original_usage = parser.usage if custom_usage else None
        if custom_usage:
            parser.usage = custom_usage

        help_text = self.format_help(parser)

        if original_usage is not None:
            parser.usage = original_usage
        if original_description is not None:
            parser.description = original_description

        examples = custom.get("examples")
        if examples:
            help_text += f"\n{self.theme.apply_header('EXAMPLES:')}\n"
            help_text += "".join(f"  {styled(e, WHITE)}\n" for e in examples)

        return help_text

    def print_help(
        self,
        parser: argparse.ArgumentParser | None = None,
        command_name: str | None = None,
        file: TextIO | None = None,
    ) -> None:
        """Print help text to the specified output."""
        parser = parser or self.cli.parser
        help_text = (
            self.format_command_help(command_name, parser)
            if command_name
            else self.format_help(parser)
        )
        (file or sys.stdout).write(help_text)

    def get_command_list(self) -> List[str]:
        """Get a list of all registered commands."""
        return list(self.cli._commands.keys())

    def add_examples(self, command_name: str, examples: List[str]) -> None:
        """Add usage examples for a command."""
        self._commands_help.setdefault(command_name, {})["examples"] = examples

    def add_long_description(self, command_name: str, description: str) -> None:
        """Add a long description for a command."""
        self._commands_help.setdefault(command_name, {})["help"] = description
