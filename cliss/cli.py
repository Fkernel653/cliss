"""Main CLI class — wraps argparse with decorator-based command registration."""

from __future__ import annotations

import argparse
import inspect
import sys
from typing import Any, Callable, Dict, List, Optional

from .argument import Argument
from .utils import get_type_from_annotation, is_bool_type


class CLI:
    """Advanced wrapper over argparse for building command-line interfaces."""

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        version: Optional[str] = None,
        auto_help: bool = True,
        colour: bool = True,
    ):
        """
        Initialize the CLI application.

        Args:
            name: Name of the application (shown in help).
            description: Description of the application (shown in help).
            version: Version string for --version flag. If provided, adds automatic version display.
            auto_help: Whether to automatically add a --help flag.
            colour: Whether to enable coloured output in help and error messages.
        """
        self.name = name
        self.description = description
        self.version = version
        self.colour = colour
        self._commands: Dict[str, dict] = {}

        parser_kwargs: Dict[str, Any] = {
            "prog": name,
            "description": description,
            "add_help": auto_help,
        }

        if colour and sys.version_info >= (3, 14):
            parser_kwargs["color"] = True
        elif colour:
            parser_kwargs["formatter_class"] = argparse.RawDescriptionHelpFormatter

        self.parser = argparse.ArgumentParser(**parser_kwargs)
        self.subparsers = self.parser.add_subparsers(dest="_command", title="Commands")

        if version:
            self.parser.add_argument("--version", action="version", version=version)

    def add_global_argument(self, *flags: str, **kwargs: Any) -> None:
        """
        Add a global argument that applies to all commands.

        Args:
            *flags: Argument flags (e.g., "--verbose", "-v").
            **kwargs: Additional keyword arguments passed to argparse.
        """
        self.parser.add_argument(*flags, **kwargs)

    def group(self, name: str, description: Optional[str] = None, **kwargs: Any) -> CLI:
        """
        Create a command group (like git remote, git stash).

        Args:
            name: Name of the group.
            description: Description shown in help.
            **kwargs: Additional keyword arguments passed to the subparser.

        Returns:
            A new CLI instance scoped to this group. Use .command() on it
            to register subcommands.
        """
        group_parser = self.subparsers.add_parser(
            name, help=description or f"{name} commands", **kwargs
        )
        group_sub = group_parser.add_subparsers(
            dest=f"_group_{name}", title="Subcommands"
        )

        sub_cli = CLI.__new__(CLI)
        sub_cli.name = name
        sub_cli.description = description
        sub_cli.version = None
        sub_cli.colour = self.colour
        sub_cli.parser = group_parser
        sub_cli.subparsers = group_sub
        sub_cli._commands = self._commands
        return sub_cli

    def command(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        arguments: Optional[List[Argument]] = None,
        **parser_kwargs: Any,
    ) -> Callable:
        """
        Decorator for creating a command.

        Args:
            name: Name of the command. If not provided, uses the function name
                  with underscores replaced by hyphens.
            description: Description of the command. If not provided, uses the
                         function's docstring.
            arguments: Optional list of Argument objects.
            **parser_kwargs: Additional keyword arguments passed to the subparser.

        Returns:
            A decorator that registers the function as a command.
        """

        def decorator(func: Callable) -> Callable:
            cmd_name = name or func.__name__.replace("_", "-")
            cmd_help = description or (func.__doc__ or "").strip()

            parser = self.subparsers.add_parser(
                cmd_name,
                help=cmd_help.split("\n")[0] if cmd_help else None,
                description=cmd_help,
                **parser_kwargs,
            )

            explicit_dests = set()

            if arguments:
                for arg in arguments:
                    kw = {
                        k: v
                        for k, v in vars(arg).items()
                        if k != "flags" and v is not None
                    }
                    action = parser.add_argument(*arg.flags, **kw)
                    explicit_dests.add(action.dest)

            sig = inspect.signature(func)
            for param_name, param in sig.parameters.items():
                if param_name in explicit_dests:
                    continue

                if param.default is inspect.Parameter.empty:
                    parser.add_argument(
                        param_name,
                        type=get_type_from_annotation(param.annotation, param.default),
                        help=param_name,
                    )
                else:
                    if is_bool_type(param):
                        self._add_bool_argument(parser, param_name, param)
                    else:
                        flag = f"--{param_name.replace('_', '-')}"
                        parser.add_argument(
                            flag,
                            type=get_type_from_annotation(
                                param.annotation, param.default
                            ),
                            default=param.default,
                            help=f"{param_name} (default: {param.default})",
                        )

            full_name = (
                f"{self.name}:{cmd_name}"
                if self.name and self.name != self.parser.prog
                else cmd_name
            )
            self._commands[full_name] = {"func": func, "parser": parser}
            return func

        return decorator

    def _add_bool_argument(
        self, parser: argparse.ArgumentParser, param_name: str, param: inspect.Parameter
    ) -> None:
        """Add a boolean argument with --name/--no-name flags."""
        base_flag = param_name.replace("_", "-")
        default_val = (
            param.default if param.default is not inspect.Parameter.empty else False
        )

        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            f"--{base_flag}",
            action="store_true",
            default=default_val,
            dest=param_name,
            help=f"Enable {param_name}",
        )
        group.add_argument(
            f"--no-{base_flag}",
            action="store_false",
            default=default_val,
            dest=param_name,
            help=f"Disable {param_name}",
        )

    def run(self, args: Optional[List[str]] = None) -> None:
        """
        Parse command-line arguments and execute the appropriate command.

        Args:
            args: List of command-line arguments. If None, uses sys.argv[1:].
        """
        args = args or sys.argv[1:]

        if not args:
            self.parser.print_help()
            return

        try:
            namespace = self.parser.parse_args(args)

            command_parts = [namespace._command]
            for key, value in vars(namespace).items():
                if key.startswith("_group_") and value:
                    command_parts.append(value)

            full_command = ":".join(command_parts)

            if full_command not in self._commands:
                self.parser.print_help()
                return

            func_kwargs = {
                k: v for k, v in vars(namespace).items() if not k.startswith("_")
            }
            result = self._commands[full_command]["func"](**func_kwargs)

            import asyncio

            if asyncio.iscoroutine(result):
                result = asyncio.run(result)

            if result is not None:
                print(result)

        except SystemExit as e:
            if e.code is not None and e.code != 0:
                raise
        except (ValueError, TypeError) as e:
            print(f"Error: {e}")
            sys.exit(1)
