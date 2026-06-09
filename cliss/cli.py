"""Main CLI class — pure sys.argv implementation with decorator-based command registration."""

from __future__ import annotations

import inspect
import sys
from typing import Any, Callable, Dict, List, NoReturn, TextIO, Tuple

from .argument import Argument
from .colors import error, info
from .help import Help
from .utils import echo, get_type_from_annotation, is_bool_type


class ArgumentDef:
    """Internal representation of a parsed argument definition."""

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
    """Pure sys.argv CLI with decorator-based command registration."""

    def __init__(
        self,
        name: str | None = None,
        usage: str = "{self.name} [COMMAND] [OPTIONS] [ARGS]...\n",
        description: str | None = None,
        version: str | None = None,
    ):
        self.name = name
        self.description = description
        self.version = version
        self.usage = usage
        self._commands: Dict[str, dict] = {}
        self._help_cache: Dict[str, str] = {}
        self._help_system = Help(self, usage=self.usage.format(self=self))
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

    @property
    def help_system(self):
        return self._help_system

    @help_system.setter
    def help_system(self, value):
        self._help_system = value

    def _error_handler(self, message: str, file: TextIO = sys.stderr) -> NoReturn:
        """Print coloured error message and exit."""
        echo(error(message), file=file)
        echo(info("See documentation or run --help"), file=file)
        sys.exit(2)

    def add_global_argument(self, *flags: str, **kwargs: Any) -> None:
        """Add a global argument that applies to all commands."""
        name = kwargs.pop("dest", None) or flags[-1].lstrip("-").replace("-", "_")
        self._global_args.append(ArgumentDef(name, list(flags), **kwargs))

    def group(self, name: str, description: str | None = None) -> CLI:
        """Create a command group."""
        sub_cli = CLI.__new__(CLI)
        sub_cli.__dict__.update(
            name=name,
            description=description,
            version=None,
            usage=self.usage,
            _commands={},
            _help_cache=self._help_cache,
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
        """Decorator for creating a command."""

        def decorator(func: Callable) -> Callable:
            cmd_name = name or func.__name__.replace("_", "-")
            cmd_help = description or (func.__doc__ or "").strip()

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
                "description": cmd_help,
                "arguments": arguments,
                "is_async": inspect.iscoroutinefunction(func),
                "group": group_prefix,
            }
            return func

        return decorator

    def _parse_arguments(
        self, args: List[str], arg_defs: List[ArgumentDef]
    ) -> Tuple[dict, List[str]]:
        """Parse arguments manually from sys.argv list."""
        parsed = {}
        positional = []
        i = 0

        flag_map = {}
        for arg_def in arg_defs:
            for flag in arg_def.flags:
                flag_map[flag] = arg_def
            if arg_def.default is not None:
                parsed[arg_def.name] = arg_def.default
            elif arg_def.action == "store_true":
                parsed[arg_def.name] = False
            elif arg_def.action == "store_false":
                parsed[arg_def.name] = True

        while i < len(args):
            arg = args[i]

            if arg in flag_map:
                arg_def = flag_map[arg]

                if arg_def.action == "version":
                    if self.version:
                        echo(self.version)
                        sys.exit(0)

                elif arg_def.action in ("store_true",):
                    parsed[arg_def.name] = True

                elif arg_def.action in ("store_false",):
                    parsed[arg_def.name] = False

                else:
                    if i + 1 < len(args) and not args[i + 1].startswith("-"):
                        i += 1
                        value = args[i]
                        try:
                            parsed[arg_def.name] = arg_def.type(value)
                        except (ValueError, TypeError):
                            parsed[arg_def.name] = value
                    else:
                        self._error_handler(f"Argument {arg} requires a value")

            elif arg.startswith("--no-"):
                name = arg[5:].replace("-", "_")
                parsed[name] = False

            else:
                positional.append(arg)

            i += 1

        for arg_def in arg_defs:
            if arg_def.name not in parsed:
                if arg_def.default is not None:
                    parsed[arg_def.name] = arg_def.default
                elif arg_def.action == "store_true":
                    parsed[arg_def.name] = False
                elif arg_def.action == "store_false":
                    parsed[arg_def.name] = True

        return parsed, positional

    def _build_arg_defs(self, cmd_info: dict) -> List[ArgumentDef]:
        """Build argument definitions from command info and function signature."""
        arg_defs = []
        explicit_dests = set()

        if cmd_info["arguments"]:
            for arg in cmd_info["arguments"]:
                kw = {
                    k: v for k, v in vars(arg).items() if k != "flags" and v is not None
                }
                arg_defs.append(
                    ArgumentDef(
                        name=kw.pop(
                            "dest", arg.flags[-1].lstrip("-").replace("-", "_")
                        ),
                        flags=list(arg.flags),
                        **kw,
                    )
                )
                explicit_dests.add(arg_defs[-1].name)

        sig = inspect.signature(cmd_info["func"])
        for param_name, param in sig.parameters.items():
            if param_name in explicit_dests:
                continue

            has_default = param.default is not inspect.Parameter.empty

            if not has_default:
                arg_defs.append(
                    ArgumentDef(
                        name=param_name,
                        flags=[param_name],
                        type=get_type_from_annotation(param.annotation, param.default),
                        required=True,
                        help=param_name,
                    )
                )
            elif is_bool_type(param):
                base_flag = param_name.replace("_", "-")
                arg_defs.append(
                    ArgumentDef(
                        name=param_name,
                        flags=[f"--{base_flag}", f"--no-{base_flag}"],
                        type=bool,
                        default=param.default
                        if param.default is not inspect.Parameter.empty
                        else False,
                        action="store_true",
                        is_bool=True,
                        help=f"Enable/disable {param_name}",
                    )
                )
            else:
                flag = f"--{param_name.replace('_', '-')}"
                arg_defs.append(
                    ArgumentDef(
                        name=param_name,
                        flags=[flag],
                        type=get_type_from_annotation(param.annotation, param.default),
                        default=param.default,
                        help=f"{param_name} (default: {param.default})",
                    )
                )

        return arg_defs

    def print_help(self, command_name: str | None = None) -> None:
        """Print help using the configured help system."""
        if command_name:
            cmd_info = self._commands.get(command_name)
            if cmd_info:
                arg_defs = self._build_arg_defs(cmd_info)
                help_text = self.help_system.format_command_help(
                    command_name,
                    cmd_info["description"],
                    arg_defs,
                )
            else:
                help_text = f"No help available for '{command_name}'"
        else:
            commands_help = {
                name: cmd["description"] for name, cmd in self._commands.items()
            }
            help_text = self.help_system.format_help(
                self.description,
                self._global_args,
                commands_help,
            )

        echo(help_text)

    def run(self, args: List[str] | None = None) -> None:
        """Parse command-line arguments and execute the appropriate command."""
        args = sys.argv[1:] if args is None else args

        global_parsed, remaining = self._parse_arguments(args, self._global_args)

        if global_parsed.get("help") or not remaining:
            cmd_name = next((a for a in remaining if not a.startswith("-")), None)
            self.print_help(cmd_name)
            return

        if global_parsed.get("version"):
            if self.version:
                echo(self.version)
            return

        command_name = remaining[0] if remaining else None
        if not command_name or command_name.startswith("-"):
            self.print_help()
            return

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
                full_name = list(group_matches.keys())[0]
                cmd_info = self._commands[full_name]
                cmd_args = remaining[1:]
            elif len(group_matches) > 1 and len(remaining) > 1:
                subcmd = remaining[1]
                full_name = f"{command_name}:{subcmd}"
                if full_name in self._commands:
                    cmd_info = self._commands[full_name]
                    cmd_args = remaining[2:]
                else:
                    self.print_help(command_name)
                    return
            else:
                self._error_handler(f"Unknown command: {command_name}")
                return

        cmd_arg_defs = self._build_arg_defs(cmd_info)

        known_flags: set[str] = set()
        for arg_def in cmd_arg_defs:
            known_flags.update(arg_def.flags)

        unknown_flags = [
            a for a in cmd_args if a.startswith("-") and a not in known_flags
        ]

        if unknown_flags:
            for flag in unknown_flags:
                echo(error(f"Unknown option: {flag}"), file=sys.stderr)
            echo(info("See documentation or run --help"), file=sys.stderr)
            sys.exit(2)

        cmd_parsed, cmd_positional = self._parse_arguments(cmd_args, cmd_arg_defs)

        func_kwargs = {**cmd_parsed}

        sig = inspect.signature(cmd_info["func"])
        positional_params = [
            name
            for name, param in sig.parameters.items()
            if param.default is inspect.Parameter.empty
        ]

        for i, pos_val in enumerate(cmd_positional):
            if i < len(positional_params):
                func_kwargs[positional_params[i]] = pos_val

        missing = [name for name in positional_params if name not in func_kwargs]
        if missing:
            self._error_handler(
                f"missing {len(missing)} required positional argument: {missing[0]!r}"
            )

        try:
            if cmd_info["is_async"]:
                import asyncio

                result = asyncio.run(cmd_info["func"](**func_kwargs))
            else:
                result = cmd_info["func"](**func_kwargs)

            if result is not None:
                echo(str(result))
        except Exception as e:
            self._error_handler(str(e))
