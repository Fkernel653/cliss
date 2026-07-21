"""Main CLI class."""

from __future__ import annotations

import inspect
import sys
from typing import Any, Callable, Dict, List, NoReturn, TextIO

from .._types.definitions import ArgumentDef
from ..colors import error, info, set_colors
from ..help import Help
from ..utils import echo, is_bool_type
from .decorators import DecoratorManager
from .parser import ArgumentParser

INFO_MESSAGE = "See documentation or run --help"


class Cliss:
    """Main CLI class for building command-line interfaces."""

    def __init__(
        self,
        name: str = "cli",
        usage: str = "{self.name} [COMMAND] [OPTIONS] [ARGS]...",
        color: bool = True,
        description: str | None = None,
        version: str | None = None,
    ):
        self.name = name
        self.color = color
        self.description = description
        self.version = version
        self._commands: Dict[str, dict] = {}
        self._help_system = Help(self, usage=usage.format(self=self), color=color)
        self._global_args: List[ArgumentDef] = []
        self._group_name: str | None = None
        self._parent_commands: Dict[str, dict] | None = None
        self._decorator_manager = DecoratorManager(self._commands)

        set_colors(self.color)

        self._parser = ArgumentParser(self._error_handler)

        if version:
            self._global_args.append(
                ArgumentDef(
                    "version",
                    ["-V", "--version"],
                    action="version",
                    help="Print version info and exit",
                )
            )
        self._global_args.append(
            ArgumentDef(
                "help",
                ["-h", "--help"],
                action="store_true",
                default=False,
                help="Print help",
            )
        )

    def _error_handler(self, message: str, file: TextIO = sys.stderr) -> NoReturn:
        echo(error(message), file=file)
        echo(info(INFO_MESSAGE), file=file)
        sys.exit(2)

    def add_global_argument(self, *flags: str, **kwargs: Any) -> None:
        name = kwargs.pop("dest", None) or flags[-1].lstrip("-").replace("-", "_")
        self._global_args.append(ArgumentDef(name, list(flags), **kwargs))

    def group(self, name: str, description: str | None = None) -> Cliss:
        sub_cli = Cliss.__new__(Cliss)
        sub_cli.__dict__.update(
            name=name,
            description=description,
            version=None,
            color=self.color,
            _commands={},
            _help_system=self._help_system,
            _global_args=[],
            _group_name=name,
            _parent_commands=self._commands,
            _decorator_manager=DecoratorManager(self._commands, self._commands),
            _parser=self._parser,
        )
        sub_cli._decorator_manager.group_name = name
        return sub_cli

    def argument(self, *args, **kwargs) -> Callable:
        return self._decorator_manager.argument(*args, **kwargs)

    def command(self, name=None, description=None, arguments=None) -> Callable:
        return self._decorator_manager.command(name, description, arguments)

    def print_help(self, command_name: str | None = None) -> None:
        if command_name and (cmd_info := self._commands.get(command_name)):
            help_text = self._help_system.format_command_help(
                command_name,
                cmd_info["description"],
                self._parser.build_arg_defs(cmd_info),
            )
        else:
            help_text = self._help_system.format_help(
                self.description,
                self._global_args,
                {name: cmd["description"] for name, cmd in self._commands.items()},
            )
        echo(help_text)

    def run(self, args: List[str] | None = None) -> None:
        args = sys.argv[1:] if args is None else args
        global_parsed, remaining = self._parser.parse_arguments(args, self._global_args)

        if global_parsed.get("help") or not remaining:
            self.print_help(next((a for a in remaining if not a.startswith("-")), None))
            return

        if global_parsed.get("version") and self.version:
            echo(self.version)
            return

        command_name = remaining[0] if remaining else None
        if not command_name or command_name.startswith("-"):
            self.print_help()
            return

        cmd_info = None
        cmd_args = []

        if command_name in self._commands:
            cmd_info = self._commands[command_name]
            cmd_args = remaining[1:]
        else:
            group_matches = {
                k: v
                for k, v in self._commands.items()
                if k.startswith(f"{command_name}:")
            }
            if len(group_matches) == 1:
                cmd_info = self._commands[list(group_matches.keys())[0]]
                cmd_args = remaining[1:]
            elif len(group_matches) > 1 and len(remaining) > 1:
                full_name = f"{command_name}:{remaining[1]}"
                if full_name in self._commands:
                    cmd_info = self._commands[full_name]
                    cmd_args = remaining[2:]

        if not cmd_info:
            main_commands = {k: v for k, v in self._commands.items() if ":" not in k}
            if not main_commands:
                self._error_handler(f"Unknown command: {command_name}")
            if len(main_commands) == 1:
                cmd_info = list(main_commands.values())[0]
                cmd_args = remaining
            else:
                self._error_handler(f"Unknown command: {command_name}")

        if not cmd_info:
            self._error_handler(f"Unknown command: {command_name}")

        cmd_arg_defs = self._parser.build_arg_defs(cmd_info)

        known_flags = {flag for arg_def in cmd_arg_defs for flag in arg_def.flags}
        unknown_flags = [
            a
            for a in cmd_args
            if a.startswith("-") and a not in known_flags and not a.startswith("--no-")
        ]

        if unknown_flags:
            file = sys.stderr
            for flag in unknown_flags:
                echo(error(f"Unknown option: {flag}"), file=file)
            echo(info(INFO_MESSAGE), file=file)
            sys.exit(2)

        cmd_parsed, cmd_positional = self._parser.parse_arguments(
            cmd_args, cmd_arg_defs
        )
        func_kwargs = {**cmd_parsed}

        sig_params = inspect.signature(cmd_info["func"]).parameters

        positional_params = [
            name
            for name, param in sig_params.items()
            if param.default is inspect.Parameter.empty and not is_bool_type(param)
        ]

        bool_positional = [
            name
            for name, param in sig_params.items()
            if param.default is inspect.Parameter.empty and is_bool_type(param)
        ]
        positional_params.extend(bool_positional)

        for i, val in enumerate(cmd_positional):
            if i < len(positional_params):
                if positional_params[i] in bool_positional:
                    func_kwargs[positional_params[i]] = val.lower() in (
                        "true",
                        "1",
                        "yes",
                        "on",
                    )
                else:
                    func_kwargs[positional_params[i]] = val

        missing = []
        for name in positional_params:
            if name not in func_kwargs:
                missing.append(name)

        if missing:
            self._error_handler(
                f"Missing {len(missing)} required positional argument: {missing[0]!r}"
            )

        try:
            result = (
                cmd_info["func"](**func_kwargs)
                if not cmd_info["is_async"]
                else __import__("asyncio").run(cmd_info["func"](**func_kwargs))
            )
            if result is not None:
                echo(str(result))
        except Exception as e:
            self._error_handler(str(e))

    def __call__(self, args: List[str] | None = None) -> None:
        return self.run(args)
