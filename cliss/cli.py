"""Main CLI class — wraps argparse with decorator-based command registration."""

from __future__ import annotations

import argparse
import inspect
import sys
from typing import Any, Callable, Dict, List, NoReturn, TextIO

from .argument import Argument
from .utils import echo, get_type_from_annotation, is_bool_type


class CLI:
    """Advanced wrapper over argparse for building command-line interfaces."""

    def __init__(
        self,
        name: str | None = None,
        description: str | None = None,
        version: str | None = None,
        usage: str = "{self.name} [COMMAND] [OPTIONS] [ARGS]...\n",
    ):
        self.name = name
        self.description = description
        self.version = version
        self.usage = usage
        self._commands: Dict[str, dict] = {}
        self._help_system = None
        self.parser = argparse.ArgumentParser(
            prog=name, description=description, add_help=False, exit_on_error=False
        )
        self.parser.error = self._error_handler  # type: ignore[assignment]
        self.subparsers = self.parser.add_subparsers(dest="_command", title="Commands")
        self.parser.usage = usage.format(self=self) if usage else None
        if version:
            self.parser.add_argument(
                "-V",
                "--version",
                action="version",
                version=version,
                help="Print version info and exit",
            )
        self.parser.add_argument(
            "-h",
            "--help",
            action="store_true",
            default=argparse.SUPPRESS,
            help="Print help",
        )

    @property
    def help_system(self):
        """Return the Help instance, creating it lazily if needed."""
        if self._help_system is None:
            from .help import Help, HelpFormatter

            self.parser.formatter_class = HelpFormatter
            self._help_system = Help(self)
        return self._help_system

    @help_system.setter
    def help_system(self, value):
        self._help_system = value

    def _error_handler(self, message: str, file: TextIO = sys.stderr) -> NoReturn:
        """Print coloured error message and exit."""
        from color_kiss.utils import error, info

        echo(error(message), file=file)
        echo(info("See documentation or run --help"), file=file)
        sys.exit(2)

    def add_global_argument(self, *flags: str, **kwargs: Any) -> None:
        """Add a global argument that applies to all commands."""
        self.parser.add_argument(*flags, **kwargs)

    def group(self, name: str, description: str | None = None, **kwargs: Any) -> CLI:
        """Create a command group."""
        group_parser = self.subparsers.add_parser(
            name, help=description or f"{name} commands", **kwargs
        )
        group_sub = group_parser.add_subparsers(
            dest=f"_group_{name}", title="Subcommands"
        )
        sub_cli = CLI.__new__(CLI)
        sub_cli.__dict__.update(
            name=name,
            description=description,
            version=None,
            usage=self.usage,
            _commands=self._commands,
            _help_system=None,
            parser=group_parser,
            subparsers=group_sub,
        )
        return sub_cli

    def command(
        self,
        name: str | None = None,
        description: str | None = None,
        arguments: List[Argument] | None = None,
        **parser_kwargs: Any,
    ) -> Callable:
        """Decorator for creating a command."""

        def decorator(func: Callable) -> Callable:
            cmd_name = name or func.__name__.replace("_", "-")
            cmd_help = description or (func.__doc__ or "").strip()
            parser = self.subparsers.add_parser(
                cmd_name,
                help=cmd_help.split("\n")[0] if cmd_help else None,
                description=cmd_help,
                add_help=False,
                **parser_kwargs,
            )
            parser.error = self._error_handler  # type: ignore[assignment]
            parser.add_argument(
                "-h",
                "--help",
                action="store_true",
                default=argparse.SUPPRESS,
                help="Print help",
            )

            explicit_dests = set()
            if arguments:
                for arg in arguments:
                    kw = {
                        k: v
                        for k, v in vars(arg).items()
                        if k != "flags" and v is not None
                    }
                    explicit_dests.add(parser.add_argument(*arg.flags, **kw).dest)

            sig = inspect.signature(func)
            for param_name, param in sig.parameters.items():
                if param_name in explicit_dests:
                    continue
                has_default = param.default is not inspect.Parameter.empty
                if not has_default:
                    parser.add_argument(
                        param_name,
                        type=get_type_from_annotation(param.annotation, param.default),
                        help=param_name,
                    )
                elif is_bool_type(param):
                    self._add_bool_argument(parser, param_name, param)
                else:
                    flag = f"--{param_name.replace('_', '-')}"
                    parser.add_argument(
                        flag,
                        type=get_type_from_annotation(param.annotation, param.default),
                        default=param.default,
                        help=f"{param_name} (default: {param.default})",
                    )

            full_name = (
                f"{self.name}:{cmd_name}"
                if self.name and self.name != self.parser.prog
                else cmd_name
            )
            self._commands[full_name] = {
                "func": func,
                "parser": parser,
                "is_async": inspect.iscoroutinefunction(func),
            }
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

    def print_help(self, command_name: str | None = None) -> None:
        """Print help using the configured help system."""
        command_info = self._commands.get(command_name) if command_name else None
        self.help_system.print_help(
            command_info["parser"] if command_info else self.parser, command_name
        )

    def _get_all_valid_flags(self) -> set:
        """Get all valid flags from all parsers."""
        valid_flags = set()
        for action in self.parser._actions:
            valid_flags.update(action.option_strings)
        for cmd_info in self._commands.values():
            for action in cmd_info["parser"]._actions:
                valid_flags.update(action.option_strings)
        return valid_flags

    def run(self, args: List[str] | None = None) -> None:
        """Parse command-line arguments and execute the appropriate command."""
        args = sys.argv[1:] if args is None else args
        if not args or any(arg in ("--help", "-h") for arg in args):
            self.print_help(
                next((arg for arg in args if not arg.startswith("-")), None)
            )
            return

        try:
            unknown_flags = [
                arg
                for arg in args
                if arg.startswith("-")
                and not any(
                    arg.startswith(flag) for flag in self._get_all_valid_flags()
                )
            ]
            if unknown_flags:
                from color_kiss.utils import error, info

                for flag in unknown_flags:
                    echo(error(f"Unknown option: {flag}"), file=sys.stderr)
                echo(info("See documentation or run --help"), file=sys.stderr)
                sys.exit(2)

            namespace = self.parser.parse_args(args)
            if getattr(namespace, "help", False) or namespace._command is None:
                self.print_help()
                return

            namespace_dict = vars(namespace)
            command_parts = [namespace._command]
            command_parts.extend(
                v for k, v in namespace_dict.items() if k.startswith("_group_") and v
            )

            command_info = self._commands.get(":".join(command_parts))
            if command_info is None:
                self.print_help()
                return

            func_kwargs = {
                k: v for k, v in namespace_dict.items() if not k.startswith("_")
            }
            if command_info["is_async"]:
                import asyncio

                result = asyncio.run(command_info["func"](**func_kwargs))
            else:
                result = command_info["func"](**func_kwargs)

            if result is not None:
                echo(str(result))
        except SystemExit as e:
            if e.code and e.code != 0:
                raise
