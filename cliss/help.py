"""Help system for CLI — extended argparse help formatting."""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING, Dict, List, Optional, TextIO, TypedDict

if TYPE_CHECKING:
    from .cli import CLI


class CommandHelpInfo(TypedDict, total=False):
    """TypedDict to store information about the team's help."""

    help: Optional[str]
    usage: Optional[str]
    examples: List[str]


class HelpTheme:
    """Theme configuration for help output in Cargo style."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    def __init__(
        self,
        usage: str = WHITE,
        header: str = BOLD + GREEN,
        option_string: str = BOLD + CYAN,
        metavar: str = BOLD + CYAN,
        description: str = DIM,
    ):
        self.usage = usage
        self.header = header
        self.option_string = option_string
        self.metavar = metavar
        self.description = description

    def apply(self, text: str, style: str) -> str:
        """Apply a style to text if colours are enabled."""
        return f"{style}{text}{self.RESET}" if text else text

    def apply_header(self, text: str) -> str:
        """Apply header style (bold green for cargo-like headers)."""
        return self.apply(text, self.header)


class HelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Extended help formatter with Cargo-style colour support."""

    def __init__(
        self,
        prog: str,
        indent_increment: int = 2,
        max_help_position: int = 24,
        width: Optional[int] = None,
    ):
        super().__init__(prog, indent_increment, max_help_position, width)
        self._help_theme = None

    def set_theme(self, theme: HelpTheme) -> None:
        """Set the colour theme."""
        self._help_theme = theme

    def _format_subparsers(self, action: argparse.Action) -> str:
        """Format subparsers without duplicate metavar line."""
        parts = []
        for name, subparser in action._name_parser_map.items():  # type: ignore[attr-defined]
            parts.append(self._format_action(subparser))
        return "\n".join(parts)

    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            prefix = "Usage: "
        formatted = super()._format_usage(usage, actions, groups, prefix)
        theme = self._help_theme
        if theme is None:
            return formatted
        lines = []
        for line in formatted.split("\n"):
            if line.startswith("Usage:"):
                parts = line.split(":", 1)
                lines.append(
                    f"{theme.apply_header('Usage:')} {theme.apply(parts[1].strip(), theme.usage)}"
                )
            else:
                lines.append(line)
        return "\n".join(lines)

    def _format_action(self, action: argparse.Action) -> str:
        if isinstance(action, argparse._SubParsersAction):
            return self._format_subparsers(action)

        result = super()._format_action(action)
        theme = self._help_theme
        if theme and action.option_strings:
            for opt in action.option_strings:
                if opt in result:
                    result = result.replace(opt, theme.apply(opt, theme.option_string))
        return result

    def _format_action_invocation(self, action: argparse.Action) -> str:
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            (metavar,) = self._metavar_formatter(action, default)(1)
            return metavar
        theme = self._help_theme
        return ", ".join(
            theme.apply(opt, theme.option_string) if theme else opt
            for opt in action.option_strings
        )

    def _metavar_formatter(self, action: argparse.Action, default_metavar: str):
        original_formatter = super()._metavar_formatter(action, default_metavar)
        theme = self._help_theme
        if theme is None:
            return original_formatter

        def coloured_formatter(size: int) -> tuple[str, ...]:
            metavars = original_formatter(size)
            return (
                tuple(theme.apply(m, theme.metavar) if m else m for m in metavars)
                if metavars
                else metavars
            )

        return coloured_formatter

    def start_section(self, heading: Optional[str]) -> None:
        if heading and self._help_theme:
            heading = self._help_theme.apply_header(heading)
        super().start_section(heading)


class Help:
    """Help system for CLI — manages help text generation and display."""

    def __init__(
        self,
        cli: "CLI",
        theme: Optional[HelpTheme] = None,
        max_help_position: int = 24,
        width: Optional[int] = None,
    ):
        """
        Initialize the help system.

        Args:
            cli: Reference to the CLI instance.
            theme: Help theme configuration.
            max_help_position: Maximum starting column for help text.
            width: Maximum width of help output.
        """
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
        help_text: Optional[str] = None,
        usage: Optional[str] = None,
        examples: Optional[List[str]] = None,
    ) -> None:
        """
        Register custom help information for a command.

        Args:
            command_name: Name of the command.
            help_text: Custom help text.
            usage: Custom usage string.
            examples: List of usage examples.
        """
        self._commands_help[command_name] = {
            "help": help_text,
            "usage": usage,
            "examples": examples or [],
        }

    def format_help(self, parser: argparse.ArgumentParser) -> str:
        """
        Format help text for a parser.

        Args:
            parser: The argument parser to generate help for.

        Returns:
            Formatted help string.
        """
        formatter = self._create_formatter(parser)
        formatter.add_usage(
            parser.usage, parser._actions, parser._mutually_exclusive_groups
        )
        if parser.description:
            formatter.add_text(parser.description)
        for action_group in parser._action_groups:
            formatter.start_section(action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()
        formatter.add_text(parser.epilog)
        return formatter.format_help()

    def format_command_help(
        self, command_name: str, parser: argparse.ArgumentParser
    ) -> str:
        """
        Format help text for a specific command.

        Args:
            command_name: Name of the command.
            parser: The command's argument parser.

        Returns:
            Formatted help string for the command.
        """
        custom = self._commands_help.get(command_name, {})
        custom_usage = custom.get("usage") if custom else None
        original_usage = None
        if custom_usage:
            original_usage, parser.usage = parser.usage, custom_usage
        help_text = self.format_help(parser)
        if original_usage is not None:
            parser.usage = original_usage
        if custom and "examples" in custom:
            help_text += f"\n{self.theme.apply_header('EXAMPLES:')}\n"
            help_text += "".join(
                f"  {self.theme.apply(e, self.theme.DIM)}\n" for e in custom["examples"]
            )
        return help_text

    def print_help(
        self,
        parser: Optional[argparse.ArgumentParser] = None,
        command_name: Optional[str] = None,
        file: Optional[TextIO] = None,
    ) -> None:
        """
        Print help text to the specified output.

        Args:
            parser: The parser to generate help for. Defaults to CLI's main parser.
            command_name: Name of the command for context-specific help.
            file: Output file. Defaults to stdout.
        """
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
        if command_name not in self._commands_help:
            self._commands_help[command_name] = {}
        self._commands_help[command_name]["examples"] = examples

    def add_long_description(self, command_name: str, description: str) -> None:
        """Add a long description for a command."""
        if command_name not in self._commands_help:
            self._commands_help[command_name] = {}
        self._commands_help[command_name]["help"] = description
