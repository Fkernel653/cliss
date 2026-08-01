"""Decorators for CLI commands."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, cast

from ..types.definitions import Argument


class DecoratorManager:
    """Manage decorators for CLI commands."""

    def __init__(
        self, commands: dict[str, dict], parent_commands: dict[str, dict] | None = None
    ):
        self._commands = commands
        self._parent_commands = parent_commands
        self._group_name = None

    @property
    def group_name(self) -> str | None:
        return self._group_name

    @group_name.setter
    def group_name(self, value: str | None) -> None:
        self._group_name = value

    def argument(
        self, *args: str | list[str | dict[str, Any]], **kwargs: Any
    ) -> Callable:
        """Decorator to customize argument flags."""

        def decorator(func):
            cli_args = getattr(func, "_cli_arguments", None)
            if cli_args is None:
                func._cli_arguments = []

            if not args and not kwargs:
                return func

            if len(args) == 1 and isinstance(args[0], list) and args[0]:
                for arg_def in args[0]:
                    if isinstance(arg_def, list):
                        self._parse_argument_definition(arg_def, func)
                    elif isinstance(arg_def, dict):
                        self._parse_argument_definition([], func, arg_def)
            else:
                flags = [a for a in args if isinstance(a, str)]
                extra_kwargs = {}
                for a in args:
                    if isinstance(a, dict):
                        extra_kwargs.update(a)
                extra_kwargs.update(kwargs)

                if flags:
                    self._parse_argument_definition(flags, func, extra_kwargs)

            return func

        return decorator

    def _parse_argument_definition(
        self, flags: list[str], func: Callable, kwargs: dict[str, Any] | None = None
    ) -> None:
        kwargs = kwargs or {}
        if flags:
            cli_args = getattr(func, "_cli_arguments", None)
            if cli_args is None:
                func._cli_arguments = []  # type: ignore
            func._cli_arguments.append({"flags": flags, **kwargs})  # type: ignore

    def command(
        self,
        name: str | None = None,
        description: str | None = None,
        arguments: list[list] | None = None,
    ) -> Callable:
        """Decorator for creating a CLI command."""

        def decorator(func: Callable) -> Callable:
            cmd_name = name or func.__name__.replace("_", "-")
            target = (
                self._parent_commands
                if self._parent_commands is not None
                else self._commands
            )
            group_prefix = self._group_name
            full_name = f"{group_prefix}:{cmd_name}" if group_prefix else cmd_name

            if arguments:
                for arg_def in arguments:
                    flags = []
                    kwargs = {}
                    for item in arg_def:
                        if isinstance(item, str):
                            flags.append(item)
                        elif isinstance(item, dict):
                            kwargs.update(item)
                    if flags:
                        cli_args = getattr(func, "_cli_arguments", None)
                        if cli_args is None:
                            func._cli_arguments = []  # type: ignore
                        cast(Any, func)._cli_arguments.append(
                            {"flags": flags, **kwargs}
                        )

            cli_args = getattr(func, "_cli_arguments", None)
            all_arguments = []

            if cli_args:
                for arg_config in cli_args:
                    flags = arg_config["flags"]
                    kwargs = {k: v for k, v in arg_config.items() if k != "flags"}
                    all_arguments.append(Argument(*flags, **kwargs))

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
