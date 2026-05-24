# cliss — A lightweight framework for building CLI applications on top of argparse

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![PyPI](https://img.shields.io/pypi/v/cliss.svg)](https://pypi.org/project/cliss/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS%20%7C%20windows-lightgrey)]()
[![Ruff](https://img.shields.io/badge/code%20style-ruff-261230?logo=ruff&logoColor=white)](https://docs.astral.sh/ruff/)

Write type-annotated Python functions, get a full CLI — automatic `--help`, validation, and async support.

## ✨ Features

- **Zero Dependencies** — Pure stdlib: `argparse`, `asyncio`, `inspect`
- **Type-Driven** — Automatic arguments from function signatures and type hints
- **Flexible** — Declarative `Argument` objects, type inference, or both
- **Async-Native** — `async def` handlers with automatic event loop management
- **Global Args** — Define flags shared across all commands
- **Coloured Help** — Beautiful terminal output via [color-kiss](https://pypi.org/project/color-kiss/), an ultra-lightweight library for readability and development speed
- **Bool Flags** — Automatic `--name`/`--no-name` mutually exclusive group
- **argparse Access** — Full access to underlying parsers for advanced use

## 🚀 Quick Start

### Installation
```bash
pip install cliss        # pip
uv pip install cliss     # uv
pipx install cliss       # pipx
```

### Usage
```python
from cliss import CLI

cli = CLI(name="todo", description="Task manager", version="1.0.0")

@cli.command()
def add(task: str, priority: int = 1, done: bool = False):
    """Add a task."""
    status = "✓" if done else "○"
    return f"[{status}] {task} (priority: {priority})"

cli.run()
```

```bash
$ python todo.py add "Buy milk" --priority 2
[○] Buy milk (priority: 2)

$ python todo.py add "Call mom" --done
[✓] Call mom (priority: 1)

$ python todo.py add "Test" --no-done
[○] Test (priority: 1)
```

## 📋 API Reference

### `CLI` class
```python
CLI(name="myapp", description="...", version="1.0.0", colour=True)
```
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `Optional[str]` | `None` | Program name in help |
| `description` | `Optional[str]` | `None` | Description in help |
| `version` | `Optional[str]` | `None` | Adds `--version` flag |
| `colour` | `bool` | `True` | Coloured output via [color-kiss](https://github.com/Fkernel653/color-kiss) |
| `usager` | `Optional[str]` | `"{self.name} [COMMAND] [OPTIONS] ...\n"` | Custom usage string |

### Colours with `color-kiss`
cliss uses [color-kiss](https://pypi.org/project/color-kiss/) — an ultra-lightweight ANSI color library — for readable, fast, and dependency-free terminal styling. No bloat, just colors.
```python
from color_kiss import BOLD_GREEN, BOLD_RED, RESET
print(f"{BOLD_GREEN}Success!{RESET}")
```

### `Argument` class
```python
from cliss import Argument

Argument("--output", "-o", type=str, default=None, help="...", choices=["json","csv"], action="store_true")
```
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `*flags` | `str` | — | Argument flags |
| `type` | `type` | `str` | Value type |
| `default` | `Any` | `None` | Default value |
| `help` | `str` | `""` | Help text |
| `required` | `bool` | `False` | Make required |
| `choices` | `list` | `None` | Allowed values |
| `action` | `str` | `None` | argparse action |

### Type → CLI Mapping
| Function Signature | CLI Argument |
|--------------------|--------------|
| `name: str` | Positional `name` |
| `count: int = 1` | `--count` (default: 1) |
| `verbose: bool = False` | `--verbose`/`--no-verbose` |
| `mode: Optional[str] = None` | `--mode` (default: None) |

## 📖 Examples

### CRUD Application
```python
from cliss import CLI

cli = CLI(name="db")
db = {}

@cli.command()
def set(key: str, value: str):
    db[key] = value
    return f"OK: {key} = {value}"

@cli.command()
def get(key: str):
    return db.get(key, "Not found")

@cli.command()
def delete(key: str, force: bool = False):
    if force or key in db:
        db.pop(key, None)
        return f"Deleted: {key}"
    return f"Not found (use --force)"

cli.run()
```

### Command Groups
```python
cli = CLI(name="git")

remote = cli.group("remote", "Manage remotes")
stash = cli.group("stash", "Stash changes")

@remote.command()
def add(name: str, url: str):
    return f"Added remote {name}"

@stash.command()
def push(message: str = ""):
    return f"Stashed: {message or 'WIP'}"

cli.run()
```

### Async Commands
```python
@cli.command()
async def fetch(url: str, retries: int = 3):
    return f"Fetched {url} (retries: {retries})"
```

## ❓ FAQ

### Why cliss over argparse/Click/Typer/Fire?
| Tool | Deps | Style |
|------|------|-------|
| **cliss** | 0 + [color-kiss](https://pypi.org/project/color-kiss/) (lightweight) | Decorators + type hints |
| Fire | 2 ([termcolor](https://pypi.org/project/termcolor/), [colorama](https://pypi.org/project/colorama/))  | Introspection |
| Click | Click | Decorators |
| Typer | Click + typing-extensions | Type hints |

cliss = Fire's zero-bloat philosophy + Typer's type-driven design. ~200 lines, pure stdlib, with [color-kiss](https://github.com/Fkernel653/color-kiss) for pretty output.

### Bool flags?
Automatic `--name`/`--no-name` mutually exclusive group. `store_true` by default, `store_false` if default is `True`.

### Async?
`async def` handlers auto-run with `asyncio.run()`. Sync functions returning coroutines also work.

### argparse access?
`cli.parser` and `cli.subparsers` are standard argparse objects. Mutually exclusive groups, custom actions, parent parsers — all available.

## 📄 License

MIT — see [LICENSE](LICENSE) file.

---

**Author:** [Fkernel653](https://github.com/Fkernel653)
**Repository:** [github.com/Fkernel653/cliss](https://github.com/Fkernel653/cliss)
**PyPI:** [pypi.org/project/cliss](https://pypi.org/project/cliss/)
