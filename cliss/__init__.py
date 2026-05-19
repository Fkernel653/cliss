import argparse
import asyncio
import inspect
import sys
import types
import typing
from typing import Any, Callable, Dict, List, Optional


def _get_type_from_annotation(annotation, default):
    """Extract a usable type from annotation, handling Union/Optional."""
    if annotation is inspect.Parameter.empty:
        return type(default) if default is not inspect.Parameter.empty else str

    # Handle Optional[str] / str | None
    origin = typing.get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        args = typing.get_args(annotation)
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            return non_none[0]
        return str

    # Handle plain types (str, int, float, etc.)
    if isinstance(annotation, type):
        return annotation

    return str


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
        self.auto_help = auto_help
        self.colour = colour

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

        if version:
            self.parser.add_argument("--version", action="version", version=version)

        self.subparsers = self.parser.add_subparsers(dest="_command", title="Commands")
        self._commands: Dict[str, dict] = {}
        self._global_args: List[Argument] = []

    def add_global_argument(self, *flags, **kwargs):
        """
        Add a global argument that applies to all commands.

        Args:
            *flags: Argument flags (e.g., "--verbose", "-v").
            **kwargs: Additional keyword arguments passed to argparse.
        """
        self._global_args.append(Argument(*flags, **kwargs))
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

            # Add explicitly specified arguments
            if arguments:
                for arg in arguments:
                    kwargs = {
                        "type": arg.type,
                        "default": arg.default,
                        "help": arg.help,
                        "required": arg.required,
                        "choices": arg.choices,
                    }

                    if arg.action:
                        kwargs["action"] = arg.action

                    action = parser.add_argument(*arg.flags, **kwargs)
                    explicit_dests.add(action.dest)

            # Automatically add arguments from the function signature
            sig = inspect.signature(func)
            for param_name, param in sig.parameters.items():
                if param_name in explicit_dests:
                    continue  # Argument already explicitly added

                if param.default is inspect.Parameter.empty:
                    # Positional argument
                    arg_type = _get_type_from_annotation(
                        param.annotation, param.default
                    )
                    parser.add_argument(param_name, type=arg_type, help=param_name)
                else:
                    # Optional argument
                    flag = f"--{param_name.replace('_', '-')}"
                    is_bool = param.annotation == bool or (
                        isinstance(param.default, bool)
                        and param.annotation in (bool, inspect.Parameter.empty)
                    )

                    if is_bool:
                        action = "store_false" if param.default else "store_true"
                        parser.add_argument(
                            flag,
                            action=action,
                            default=param.default,
                            help=f"{param_name} (default: {param.default})",
                        )
                    else:
                        arg_type = _get_type_from_annotation(
                            param.annotation, param.default
                        )
                        parser.add_argument(
                            flag,
                            type=arg_type,
                            default=param.default,
                            help=f"{param_name} (default: {param.default})",
                        )

            self._commands[cmd_name] = {"func": func, "parser": parser}

            return func

        return decorator

    def run(self, args: Optional[List[str]] = None) -> None:
        """
        Parse command-line arguments and execute the appropriate command.

        Args:
            args: List of command-line arguments. If None, uses sys.argv[1:].

        Raises:
            SystemExit: If argument parsing fails or an error occurs during execution.
        """
        if args is None:
            args = sys.argv[1:]

        if not args:
            self.parser.print_help()
            return

        try:
            namespace = self.parser.parse_args(args)

            command = getattr(namespace, "_command", None)
            if not command or command not in self._commands:
                self.parser.print_help()
                return

            cmd_data = self._commands[command]
            func_kwargs = {k: v for k, v in vars(namespace).items() if k != "_command"}

            result = cmd_data["func"](**func_kwargs)
            if asyncio.iscoroutine(result):
                result = asyncio.run(result)

            if result is not None:
                print(result)

        except SystemExit as e:
            if e.code is not None and e.code != 0:
                raise
        except (ValueError, TypeError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
