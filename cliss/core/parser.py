"""Argument parsing utilities."""

from __future__ import annotations

import inspect
from typing import Callable, List, NoReturn

from .._types.definitions import ArgumentDef
from ..utils import get_type_from_annotation, is_bool_type


class ArgumentParser:
    """Parse command-line arguments."""

    def __init__(self, error_handler: Callable[[str], NoReturn]):
        self._error_handler = error_handler

    def parse_arguments(
        self, args: List[str], arg_defs: List[ArgumentDef]
    ) -> tuple[dict, List[str]]:
        """Parse arguments against definitions."""
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

                if arg_def.action == "version":
                    parsed[arg_def.name] = True
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

    def build_arg_defs(self, cmd_info: dict) -> List[ArgumentDef]:
        """Build argument definitions from command info."""
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
