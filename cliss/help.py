"""Help system for CLI — extended argparse help formatting."""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, TextIO, TypedDict

if TYPE_CHECKING:
    from .cli import CLI


class CommandHelpInfo(TypedDict, total=False):
    """TypedDict to store information about the team's help."""

    help: Optional[str]
    usage: Optional[str]
    examples: List[str]


class HelpFormatter(argparse.HelpFormatter):
    """Extended help formatter with colour support and custom formatting."""

    def __init__(
        self,
        prog: str,
        indent_increment: int = 2,
        max_help_position: int = 24,
        width: Optional[int] = None,
        colour: bool = True,
    ):
        super().__init__(prog, indent_increment, max_help_position, width)
        self.colour = colour

    def _format_usage(
        self,
        usage: Optional[str],
        actions: Iterable[argparse.Action],
        groups: Iterable[argparse._ArgumentGroup],
        prefix: Optional[str],
    ) -> str:
        if prefix is None:
            prefix = "Usage: "
        return super()._format_usage(usage, actions, groups, prefix)

    def _format_action(self, action: argparse.Action) -> str:
        """Override to add colour and custom formatting for actions."""
        result = super()._format_action(action)
        return result

    def _format_action_invocation(self, action: argparse.Action) -> str:
        """Override to format action invocations with colour."""
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            (metavar,) = self._metavar_formatter(action, default)(1)
            return metavar

        parts = []
        if action.option_strings:
            parts.extend(action.option_strings)
        return ", ".join(parts)

    def _metavar_formatter(self, action: argparse.Action, default_metavar: str):
        """Override to add colour to metavar."""
        if action.metavar is not None:
            result = super()._metavar_formatter(action, default_metavar)
        else:
            result = super()._metavar_formatter(action, default_metavar)
        return result


class HelpTheme:
    """Theme configuration for help output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"

    def __init__(
        self,
        usage: str = BOLD,
        header: str = BOLD,
        option_string: str = GREEN,
        metavar: str = YELLOW,
        description: str = DIM,
    ):
        self.usage = usage
        self.header = header
        self.option_string = option_string
        self.metavar = metavar
        self.description = description


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
        formatter = parser._get_formatter()

        # Usage
        formatter.add_usage(
            parser.usage,
            parser._actions,
            parser._mutually_exclusive_groups,
        )

        # Description
        if parser.description:
            formatter.add_text(parser.description)

        # Positionals, optionals, user-defined groups
        for action_group in parser._action_groups:
            formatter.start_section(action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()

        # Epilog
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

        if custom:
            custom_usage = custom.get("usage")
            if custom_usage:
                parser.usage = custom_usage

        help_text = self.format_help(parser)

        if custom:
            examples = custom.get("examples", [])
            if examples:
                help_text += "\nExamples:\n"
                for example in examples:
                    help_text += f"  {example}\n"

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

        if command_name:
            help_text = self.format_command_help(command_name, parser)
        else:
            help_text = self.format_help(parser)

        (file or sys.stdout).write(help_text)

    def get_command_list(self) -> List[str]:
        """
        Get a list of all registered commands.

        Returns:
            List of command names.
        """
        return list(self.cli._commands.keys())

    def add_examples(self, command_name: str, examples: List[str]) -> None:
        """
        Add usage examples for a command.

        Args:
            command_name: Name of the command.
            examples: List of example strings.
        """
        if command_name not in self._commands_help:
            self._commands_help[command_name] = {}
        self._commands_help[command_name]["examples"] = examples

    def add_long_description(self, command_name: str, description: str) -> None:
        """
        Add a long description for a command.

        Args:
            command_name: Name of the command.
            description: Extended description text.
        """
        if command_name not in self._commands_help:
            self._commands_help[command_name] = {}
        self._commands_help[command_name]["help"] = description
