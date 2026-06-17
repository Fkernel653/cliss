"""Main CLI class — pure sys.argv implementation with decorator-based command registration."""

from __future__ import annotations

import inspect
import sys
from typing import Any, Callable, Dict, List, NoReturn, TextIO

from .argument import Argument
from .colors import error, info, set_colors
from .help import Help
from .utils import echo, get_type_from_annotation, is_bool_type

INFO_MESSAGE = "See documentation or run --help"


class ArgumentDef:
    """Definition of a command-line argument or option."""

    __slots__ = (
        "name",
        "flags",
        "help_flags",
        "default",
        "type",
        "help",
        "action",
        "required",
        "is_bool",
        "negated_flag",
    )

    def __init__(
        self, name: str, flags: List[str], help_flags: List[str] | None = None, **kwargs
    ):
        """
        Initialize an argument definition for CLI command parsing.

        Args:
            name: Internal name of the argument (used as key in parsed kwargs).
            flags: All valid command-line flags for parsing (e.g., ['-s', '--string', '--no-string']).
            help_flags: Subset of flags to display in help text. If None, defaults to all flags.
            **kwargs: Additional argument options:
                default: Default value if argument is not provided.
                type: Expected type for value casting (default: str).
                help: Description text for help output.
                action: Special action handler ('store_true', 'store_false', 'version').
                required: Whether the argument must be provided (default: False).
                is_bool: Whether this is a boolean flag argument (default: False).
                negated_flag: The negated version of the flag (e.g., '--no-string').

        Example:
            >>> # Boolean flag with default False (shows --string in help)
            >>> ArgumentDef(
            ...     "string",
            ...     ["-s", "--string", "--no-string"],
            ...     help_flags=["-s", "--string"],
            ...     type=bool,
            ...     default=False,
            ...     action="store_true",
            ...     is_bool=True,
            ...     help="Enable string mode",
            ...     negated_flag="--no-string"
            ... )
        """
        self.name = name
        self.flags = flags
        self.help_flags = help_flags if help_flags is not None else flags
        self.default = kwargs.get("default")
        self.type = kwargs.get("type", str)
        self.help = kwargs.get("help", "")
        self.action = kwargs.get("action")
        self.required = kwargs.get("required", False)
        self.is_bool = kwargs.get("is_bool", False)
        self.negated_flag = kwargs.get("negated_flag")


class CLI:
    """
    Main CLI class for building command-line interfaces with decorators.

    Features:
        - Decorator-based command registration
        - Automatic argument parsing from function signatures
        - Support for boolean flags with --flag/--no-flag patterns
        - Command grouping
        - Colored output
        - Built-in help and version commands

    Example:
        >>> app = CLI(name="myapp", description="My awesome CLI")
        >>>
        >>> @app.command()
        >>> def hello(name: str, verbose: bool = False):
        >>>     if verbose:
        >>>         print(f"Hello, {name}!")
        >>>     else:
        >>>         print(f"Hi {name}")
        >>>
        >>> if __name__ == "__main__":
        >>>     app.run()
    """

    def __init__(
        self,
        name: str = "cli",
        usage: str = "{self.name} [COMMAND] [OPTIONS] [ARGS]...",
        color: bool = True,
        description: str | None = None,
        version: str | None = None,
    ):
        """
        Initialize the CLI application.

        Args:
            name: Name of the CLI application (shown in help)
            usage: Usage string template (can use {self.name})
            color: Whether to use colored output
            description: Application description (shown in help)
            version: Version string (enables --version flag)

        Example:
            >>> app = CLI(
            ...     name="mycli",
            ...     description="A simple CLI tool",
            ...     version="1.0.0"
            ... )
        """
        self.name = name
        self.color = color
        self.description = description
        self.version = version
        self._commands: Dict[str, dict] = {}
        self._help_system = Help(self, usage=usage.format(self=self), color=color)
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
        """Handle errors by printing message and exiting."""
        if not self.color:
            set_colors(False)
        echo(error(message), file=file)
        echo(info(INFO_MESSAGE), file=file)
        sys.exit(2)

    def add_global_argument(self, *flags: str, **kwargs: Any) -> None:
        """
        Add a global argument/flag available to all commands.

        Args:
            *flags: Command-line flags (e.g., '-v', '--verbose')
            **kwargs: Additional options:
                dest: Internal name (defaults to last flag without dashes)
                default: Default value
                type: Type to cast to
                help: Help text
                action: Special action ('store_true', 'store_false')
                required: Whether required

        Example:
            >>> app.add_global_argument(
            ...     '-v', '--verbose',
            ...     action='store_true',
            ...     help='Enable verbose output'
            ... )
        """
        name = kwargs.pop("dest", None) or flags[-1].lstrip("-").replace("-", "_")
        self._global_args.append(ArgumentDef(name, list(flags), **kwargs))

    def group(self, name: str, description: str | None = None) -> CLI:
        """
        Create a command group for organizing related commands.

        Commands in a group are prefixed with the group name (e.g., 'group:command').
        This is useful for organizing large CLIs with many commands.

        Args:
            name: Name of the group
            description: Description of the group (shown in help)

        Returns:
            A new CLI instance for registering grouped commands

        Example:
            >>> app = CLI()
            >>>
            >>> # Create a group
            >>> db = app.group('db', 'Database operations')
            >>>
            >>> @db.command()
            >>> def migrate():
            >>>     \"\"\"Run database migrations.\"\"\"
            >>>     print("Migrating...")
            >>>
            >>> # Command is accessible as 'db:migrate' or 'db migrate'
        """
        sub_cli = CLI.__new__(CLI)
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
        )
        return sub_cli

    def argument(self, *flags: str, **kwargs: Any) -> Callable:
        """
        Decorator to add argument configuration to a command function.

        Args:
            *flags: Command-line flags (e.g., '-s', '--string')
            **kwargs: Additional options (dest, help, type, required, choices, action, etc.)

        Returns:
            Decorator that adds argument metadata to the function
        """

        def decorator(func):
            if not hasattr(func, "_cli_arguments"):
                setattr(func, "_cli_arguments", [])
            func._cli_arguments.append({"flags": list(flags), **kwargs})
            return func

        return decorator

    def command(
        self,
        name: str | None = None,
        description: str | None = None,
        arguments: List[Argument] | None = None,
    ) -> Callable:
        """
        Decorator to register a function as a CLI command.

        The decorated function's parameters become command arguments:
        - Parameters with defaults become optional flags (--param)
        - Parameters without defaults become positional arguments
        - Boolean parameters become --flag/--no-flag options
        - Use @app.argument() alongside this decorator for custom flags

        Args:
            name: Custom command name (defaults to function name with underscores replaced by dashes)
            description: Command description (defaults to function docstring)
            arguments: List of Argument objects for explicit argument definitions

        Returns:
            Decorator function that registers the command

        Example:
            >>> @app.command()
            >>> def greet(name: str, uppercase: bool = False):
            >>>     \"\"\"Greet a person by name.\"\"\"
            >>>     msg = f"Hello, {name}!"
            >>>     if uppercase:
            >>>         msg = msg.upper()
            >>>     print(msg)
            >>>
            >>> # Usage:
            >>> # $ mycli greet Alice
            >>> # Hello, Alice!
            >>> # $ mycli greet Bob --uppercase
            >>> # HELLO, BOB!
        """

        def decorator(func: Callable) -> Callable:
            cmd_name = name or func.__name__.replace("_", "-")
            target = (
                self._parent_commands
                if self._parent_commands is not None
                else self._commands
            )
            group_prefix = getattr(self, "_group_name", None)
            full_name = f"{group_prefix}:{cmd_name}" if group_prefix else cmd_name

            all_arguments = list(arguments) if arguments else []

            cli_args = getattr(func, "_cli_arguments", None)
            if cli_args:
                for arg_config in cli_args:
                    flags = arg_config.pop("flags")
                    all_arguments.append(Argument(*flags, **arg_config))

            target[full_name] = {
                "func": func,
                "name": cmd_name,
                "full_name": full_name,
                "description": description or (func.__doc__ or "").strip(),
                "arguments": all_arguments if all_arguments else None,
                "is_async": inspect.iscoroutinefunction(func),
                "group": group_prefix,
            }
            return func

        return decorator

    def _parse_arguments(
        self, args: List[str], arg_defs: List[ArgumentDef]
    ) -> tuple[dict, List[str]]:
        """
        Parse command-line arguments against argument definitions.

        Args:
            args: List of argument strings
            arg_defs: List of argument definitions

        Returns:
            Tuple of (parsed dictionary, remaining positional arguments)
        """
        parsed = {}
        positional = []
        i = 0

        flag_map = {}
        negated_map = {}
        bool_defaults = {}

        for arg_def in arg_defs:
            for flag in arg_def.flags:
                flag_map[flag] = arg_def
            if arg_def.is_bool and arg_def.negated_flag:
                negated_map[arg_def.negated_flag] = arg_def
            if arg_def.is_bool:
                bool_defaults[arg_def.name] = arg_def.default

        for arg_def in arg_defs:
            if arg_def.default is not None:
                parsed[arg_def.name] = arg_def.default
            elif arg_def.action in ("store_true", "store_false"):
                parsed[arg_def.name] = arg_def.action == "store_true"

        while i < len(args):
            arg = args[i]

            if arg in negated_map:
                arg_def = negated_map[arg]
                parsed[arg_def.name] = False
                i += 1
                continue

            if arg in flag_map:
                arg_def = flag_map[arg]

                if arg_def.action == "version" and self.version:
                    echo(self.version)
                    sys.exit(0)
                elif arg_def.action in ("store_true", "store_false"):
                    parsed[arg_def.name] = True
                else:
                    if i + 1 < len(args) and not args[i + 1].startswith("-"):
                        i += 1
                        try:
                            parsed[arg_def.name] = arg_def.type(args[i])
                        except (ValueError, TypeError):
                            parsed[arg_def.name] = args[i]
                    else:
                        self._error_handler(f"Argument {arg} requires a value")
                i += 1
                continue

            if arg.startswith("--no-"):
                name = arg[5:].replace("-", "_")
                if name in bool_defaults:
                    parsed[name] = False
                    i += 1
                    continue

            positional.append(arg)
            i += 1

        return parsed, positional

    def _build_arg_defs(self, cmd_info: dict) -> List[ArgumentDef]:
        """
        Build argument definitions from a command's function signature.
        """
        arg_defs = []
        explicit_dests = set()

        if cmd_info["arguments"]:
            for arg in cmd_info["arguments"]:
                kw = {
                    k: v for k, v in vars(arg).items() if k != "flags" and v is not None
                }
                name = kw.pop("dest", None) or arg.flags[-1].lstrip("-").replace(
                    "-", "_"
                )

                is_store_action = kw.get("action") in ("store_true", "store_false")
                is_bool_type_arg = kw.get("type") is bool

                if is_store_action or is_bool_type_arg:
                    long_flags = [f for f in arg.flags if f.startswith("--")]
                    if long_flags:
                        base = long_flags[0]
                        negated = f"--no-{base[2:]}"
                        all_flags = list(arg.flags) + [negated]
                        kw["is_bool"] = True
                        kw["negated_flag"] = negated
                    else:
                        all_flags = list(arg.flags)
                        kw["is_bool"] = True
                else:
                    all_flags = list(arg.flags)

                arg_defs.append(ArgumentDef(name, all_flags, **kw))
                explicit_dests.add(name)

        for param_name, param in inspect.signature(cmd_info["func"]).parameters.items():
            if param_name in explicit_dests:
                continue

            is_bool = is_bool_type(param)
            has_default = param.default is not inspect.Parameter.empty

            if is_bool:
                base_flag = param_name.replace("_", "-")
                short_flag = f"-{param_name[0]}"

                if has_default:
                    default_value = param.default
                    required = False

                    all_flags = [short_flag, f"--{base_flag}", f"--no-{base_flag}"]
                    negated_flag = f"--no-{base_flag}"

                    if default_value is True:
                        help_flags = [f"--no-{base_flag}"]
                        help_text = f"Disable {param_name} (default: enabled)"
                    else:
                        help_flags = [short_flag, f"--{base_flag}"]
                        help_text = f"Enable {param_name} (default: disabled)"
                else:
                    default_value = False
                    required = True
                    all_flags = [short_flag, f"--{base_flag}", f"--no-{base_flag}"]
                    negated_flag = f"--no-{base_flag}"
                    help_flags = [short_flag, f"--{base_flag}", f"--no-{base_flag}"]
                    help_text = f"Enable/disable {param_name} (required)"

                arg_defs.append(
                    ArgumentDef(
                        param_name,
                        all_flags,
                        help_flags=help_flags,
                        type=bool,
                        default=default_value,
                        action="store_true",
                        is_bool=True,
                        required=required,
                        help=help_text,
                        negated_flag=negated_flag,
                    )
                )
            elif param.default is inspect.Parameter.empty:
                arg_defs.append(
                    ArgumentDef(
                        param_name,
                        [param_name],
                        type=get_type_from_annotation(param.annotation, param.default),
                        required=True,
                        help=param_name,
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
        """
        Print help information for the CLI or a specific command.

        Args:
            command_name: Name of the command to show help for (None for global help)

        Example:
            >>> app.print_help()  # Show global help
            >>> app.print_help('greet')  # Show help for 'greet' command
        """
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
        """
        Parse arguments and execute the appropriate command.

        This is the main entry point for the CLI. It parses command-line arguments,
        finds the matching command, parses command-specific arguments, and executes
        the command function.

        Args:
            args: Command-line arguments (defaults to sys.argv[1:])

        Returns:
            None (exits with status code on error)

        Example:
            >>> if __name__ == "__main__":
            >>>     app.run()
            >>>
            >>> # Or with custom arguments:
            >>> app.run(["greet", "Alice", "--uppercase"])

        Raises:
            SystemExit: On error or help display
        """
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

        cmd_arg_defs = self._build_arg_defs(cmd_info)

        known_flags = {flag for arg_def in cmd_arg_defs for flag in arg_def.flags}
        unknown_flags = [
            a
            for a in cmd_args
            if a.startswith("-") and a not in known_flags and not a.startswith("--no-")
        ]

        if unknown_flags:
            if not self.color:
                set_colors(False)
            file = sys.stderr
            for flag in unknown_flags:
                echo(error(f"Unknown option: {flag}"), file=file)
            echo(info(INFO_MESSAGE), file=file)
            sys.exit(2)

        cmd_parsed, cmd_positional = self._parse_arguments(cmd_args, cmd_arg_defs)
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
        """
        Make the CLI instance callable, delegating to run().

        Args:
            args: Command-line arguments (defaults to sys.argv[1:])

        Example:
            >>> app = CLI()
            >>> app()  # Equivalent to app.run()
        """
        return self.run(args)
