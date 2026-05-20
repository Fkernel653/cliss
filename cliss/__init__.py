from __future__ import annotations

import argparse
import inspect
import sys
from typing import Any, Callable, Dict, List, Optional, Union, get_args, get_origin


def _get_type_from_annotation(annotation, default):
    """Extract a usable type from annotation, handling Union/Optional."""
    from types import UnionType

    if annotation is inspect.Parameter.empty:
        return type(default) if default is not inspect.Parameter.empty else str

    if isinstance(annotation, str):
        if default is not inspect.Parameter.empty:
            return type(default)
        return str

    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        non_none = [a for a in get_args(annotation) if a is not type(None)]
        return non_none[0] if non_none else str

    return annotation if isinstance(annotation, type) else str


class Argument:
    """Description of an argument for a command."""

    def __init__(
        self,
        *flags: str,
        type: type = str,
        default: Any = None,
        help: str = "",
        required: bool = False,
        choices: Optional[List[Any]] = None,
        action: Optional[str] = None,
    ):
        """
        Initialize a command argument descriptor.

        Args:
            *flags: Argument flags (e.g., "--output", "-o").
            type: Expected type of the argument value.
            default: Default value if the argument is not provided.
            help: Help text describing the argument.
            required: Whether the argument must be provided.
            choices: List of allowed values for the argument.
            action: Custom argparse action (e.g., "store_true", "store_false").
        """
        self.flags = flags
        self.type = type
        self.default = default
        self.help = help
        self.required = required
        self.choices = choices
        self.action = action


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

        parser_kwargs = {
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

    def add_global_argument(self, *flags, **kwargs):
        """
        Add a global argument that applies to all commands.

        Args:
            *flags: Argument flags (e.g., "--verbose", "-v").
            **kwargs: Additional keyword arguments passed to argparse.
        """
        self.parser.add_argument(*flags, **kwargs)

    def command(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        arguments: Optional[List[Argument]] = None,
        **parser_kwargs,
    ) -> Callable:
        """
        Decorator for creating a command.

        You can pass a list of Argument objects or use type annotations in the function
        to automatically generate arguments.

        Args:
            name: Name of the command. If not provided, uses the function name
                  with underscores replaced by hyphens.
            description: Description of the command. If not provided, uses the
                         function's docstring.
            arguments: Optional list of Argument objects describing the command's
                       arguments.
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
                    kwargs = {
                        k: v
                        for k, v in vars(arg).items()
                        if k != "flags" and v is not None
                    }
                    action = parser.add_argument(*arg.flags, **kwargs)
                    explicit_dests.add(action.dest)

            sig = inspect.signature(func)
            for param_name, param in sig.parameters.items():
                if param_name in explicit_dests:
                    continue

                if param.default is inspect.Parameter.empty:
                    arg_type = _get_type_from_annotation(
                        param.annotation, param.default
                    )
                    parser.add_argument(param_name, type=arg_type, help=param_name)
                else:
                    is_bool = self._is_bool_type(param)

                    if is_bool:
                        self._add_bool_argument(parser, param_name, param)
                    else:
                        flag = f"--{param_name.replace('_', '-')}"
                        parser.add_argument(
                            flag,
                            type=_get_type_from_annotation(
                                param.annotation, param.default
                            ),
                            default=param.default,
                            help=f"{param_name} (default: {param.default})",
                        )

            self._commands[cmd_name] = {"func": func, "parser": parser}
            return func

        return decorator

    def _is_bool_type(self, param: inspect.Parameter) -> bool:
        annotation = param.annotation

        if isinstance(annotation, str):
            return annotation == "bool"

        if annotation == bool:
            return True
        if isinstance(param.default, bool) and annotation in (
            bool,
            inspect.Parameter.empty,
        ):
            return True
        return False

    def _add_bool_argument(self, parser, param_name: str, param: inspect.Parameter):
        """Add boolean argument with automatic --name/--no-name flags."""
        base_flag = param_name.replace("_", "-")
        flag_on = f"--{base_flag}"
        flag_off = f"--no-{base_flag}"

        default_val = (
            param.default if param.default is not inspect.Parameter.empty else False
        )

        group = parser.add_mutually_exclusive_group()

        group.add_argument(
            flag_on,
            action="store_true",
            default=default_val,
            dest=param_name,
            help=f"Enable {param_name}",
        )

        group.add_argument(
            flag_off,
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

        Raises:
            SystemExit: If argument parsing fails or an error occurs during execution.
        """
        args = args or sys.argv[1:]

        if not args:
            self.parser.print_help()
            return

        try:
            namespace = self.parser.parse_args(args)
            command = getattr(namespace, "_command", None)

            if not command or command not in self._commands:
                self.parser.print_help()
                return

            func_kwargs = {k: v for k, v in vars(namespace).items() if k != "_command"}
            result = self._commands[command]["func"](**func_kwargs)

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
