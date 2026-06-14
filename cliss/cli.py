"""Main CLI class — pure sys.argv implementation with decorator-based command registration."""

from __future__ import annotations

import inspect
import sys
from typing import Any, Callable, Dict, List, NoReturn, TextIO

from .argument import Argument
from .colors import error, info
from .help import Help
from .utils import echo, get_type_from_annotation, is_bool_type

ERROR_PREFIX = "Error: "
INFO_PREFIX = "Info: "
INFO_MESSAGE = "See documentation or run --help"


class ArgumentDef:
    __slots__ = (
        "name",
        "flags",
        "default",
        "type",
        "help",
        "action",
        "required",
        "is_bool",
    )

    def __init__(self, name: str, flags: List[str], **kwargs):
        self.name = name
        self.flags = flags
        self.default = kwargs.get("default")
        self.type = kwargs.get("type", str)
        self.help = kwargs.get("help", "")
        self.action = kwargs.get("action")
        self.required = kwargs.get("required", False)
        self.is_bool = kwargs.get("is_bool", False)


class CLI:
    def __init__(
        self,
        name: str = "cli",
        usage: str = "{self.name} [COMMAND] [OPTIONS] [ARGS]...",
        colour: bool = True,
        description: str | None = None,
        version: str | None = None,
    ):
        self.name = name
        self.colour = colour
        self.description = description
        self.version = version
        self._commands: Dict[str, dict] = {}
        self._help_system = Help(self, usage=usage.format(self=self), colour=colour)
        self._global_args: List[ArgumentDef] = []
        self._group_name: str | None = None
        self._parent_commands: Dict[str, dict] | None = None

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
        if self.colour:
            echo(error(message), file=file)
            echo(info(INFO_MESSAGE), file=file)
        else:
            echo(f"{ERROR_PREFIX}{message}\n{INFO_PREFIX}{INFO_MESSAGE}", file=file)
        sys.exit(2)

    def add_global_argument(self, *flags: str, **kwargs: Any) -> None:
        name = kwargs.pop("dest", None) or flags[-1].lstrip("-").replace("-", "_")
        self._global_args.append(ArgumentDef(name, list(flags), **kwargs))

    def group(self, name: str, description: str | None = None) -> CLI:
        sub_cli = CLI.__new__(CLI)
        sub_cli.__dict__.update(
            name=name,
            description=description,
            version=None,
            colour=self.colour,
            _commands={},
            _help_system=self._help_system,
            _global_args=[],
            _group_name=name,
            _parent_commands=self._commands,
        )
        return sub_cli

    def command(
        self,
        name: str | None = None,
        description: str | None = None,
        arguments: List[Argument] | None = None,
    ) -> Callable:
        def decorator(func: Callable) -> Callable:
            cmd_name = name or func.__name__.replace("_", "-")
            target = (
                self._parent_commands
                if self._parent_commands is not None
                else self._commands
            )
            group_prefix = getattr(self, "_group_name", None)
            full_name = f"{group_prefix}:{cmd_name}" if group_prefix else cmd_name

            target[full_name] = {
                "func": func,
                "name": cmd_name,
                "full_name": full_name,
                "description": description or (func.__doc__ or "").strip(),
                "arguments": arguments,
                "is_async": inspect.iscoroutinefunction(func),
                "group": group_prefix,
            }
            return func

        return decorator

    def _parse_arguments(
        self, args: List[str], arg_defs: List[ArgumentDef]
    ) -> tuple[dict, List[str]]:
        parsed = {}
        positional = []
        i = 0
        flag_map = {flag: arg_def for arg_def in arg_defs for flag in arg_def.flags}

        for arg_def in arg_defs:
            if arg_def.default is not None:
                parsed[arg_def.name] = arg_def.default
            elif arg_def.action in ("store_true", "store_false"):
                parsed[arg_def.name] = arg_def.action == "store_false"

        while i < len(args):
            arg = args[i]

            if arg in flag_map:
                arg_def = flag_map[arg]

                if arg_def.action == "version" and self.version:
                    echo(self.version)
                    sys.exit(0)
                elif arg_def.action in ("store_true", "store_false"):
                    parsed[arg_def.name] = arg_def.action == "store_true"
                else:
                    if i + 1 < len(args) and not args[i + 1].startswith("-"):
                        i += 1
                        try:
                            parsed[arg_def.name] = arg_def.type(args[i])
                        except (ValueError, TypeError):
                            parsed[arg_def.name] = args[i]
                    else:
                        self._error_handler(f"Argument {arg} requires a value")
            elif arg.startswith("--no-"):
                parsed[arg[5:].replace("-", "_")] = False
            else:
                positional.append(arg)
            i += 1

        return parsed, positional

    def _build_arg_defs(self, cmd_info: dict) -> List[ArgumentDef]:
        arg_defs = []
        explicit_dests = set()

        if cmd_info["arguments"]:
            for arg in cmd_info["arguments"]:
                kw = {
                    k: v for k, v in vars(arg).items() if k != "flags" and v is not None
                }
                name = kw.pop("dest", arg.flags[-1].lstrip("-").replace("-", "_"))
                arg_defs.append(ArgumentDef(name, list(arg.flags), **kw))
                explicit_dests.add(name)

        for param_name, param in inspect.signature(cmd_info["func"]).parameters.items():
            if param_name in explicit_dests:
                continue

            if param.default is inspect.Parameter.empty:
                arg_defs.append(
                    ArgumentDef(
                        param_name,
                        [param_name],
                        type=get_type_from_annotation(param.annotation, param.default),
                        required=True,
                        help=param_name,
                    )
                )
            elif is_bool_type(param):
                base_flag = param_name.replace("_", "-")
                arg_defs.append(
                    ArgumentDef(
                        param_name,
                        [f"--{base_flag}", f"--no-{base_flag}"],
                        type=bool,
                        default=param.default,
                        action="store_true",
                        is_bool=True,
                        help=f"Enable/disable {param_name}",
                    )
                )
            else:
                arg_defs.append(
                    ArgumentDef(
                        param_name,
                        [f"--{param_name.replace('_', '-')}"],
                        type=get_type_from_annotation(param.annotation, param.default),
                        default=param.default,
                        help=f"{param_name} (default: {param.default})",
                    )
                )

        return arg_defs

    def print_help(self, command_name: str | None = None) -> None:
        if command_name and (cmd_info := self._commands.get(command_name)):
            help_text = self._help_system.format_command_help(
                command_name, cmd_info["description"], self._build_arg_defs(cmd_info)
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
        global_parsed, remaining = self._parse_arguments(args, self._global_args)

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
            self._error_handler(f"Unknown command: {command_name}")

        cmd_arg_defs = self._build_arg_defs(cmd_info)
        known_flags = {flag for arg_def in cmd_arg_defs for flag in arg_def.flags}
        unknown_flags = [
            a for a in cmd_args if a.startswith("-") and a not in known_flags
        ]

        if unknown_flags:
            for flag in unknown_flags:
                echo(
                    error(f"Unknown option: {flag}")
                    if self.colour
                    else f"{ERROR_PREFIX}Unknown option: {flag}",
                    file=sys.stderr,
                )
            echo(
                info(INFO_MESSAGE) if self.colour else f"{INFO_PREFIX}{INFO_MESSAGE}",
                file=sys.stderr,
            )
            sys.exit(2)

        cmd_parsed, cmd_positional = self._parse_arguments(cmd_args, cmd_arg_defs)
        func_kwargs = {**cmd_parsed}

        positional_params = [
            name
            for name, param in inspect.signature(cmd_info["func"]).parameters.items()
            if param.default is inspect.Parameter.empty
        ]
        for i, val in enumerate(cmd_positional):
            if i < len(positional_params):
                func_kwargs[positional_params[i]] = val

        missing = [name for name in positional_params if name not in func_kwargs]
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
