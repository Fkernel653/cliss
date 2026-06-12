# cliss — A lightweight framework for building CLI applications

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![PyPI](https://img.shields.io/pypi/v/cliss.svg)](https://pypi.org/project/cliss/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS%20%7C%20windows-lightgrey)]()
[![Ruff](https://img.shields.io/badge/code%20style-ruff-261230?logo=ruff&logoColor=white)](https://docs.astral.sh/ruff/)

Write type-annotated Python functions, get a full CLI — automatic `--help`, validation, async support, and zero dependencies.

## ✨ Features

- **Zero Dependencies** — Pure stdlib: `sys`, `asyncio`, `inspect`
- **Type-Driven** — Automatic arguments from function signatures and type hints
- **Flexible** — Declarative `Argument` objects, type inference, or both
- **Async-Native** — `async def` handlers with automatic event loop management
- **Global Args** — Define flags shared across all commands
- **Coloured Help** — Beautiful terminal output via ANSI-codes (can be disabled)
- **Bool Flags** — Automatic `--name`/`--no-name` mutually exclusive group
- **Manual Parsing** — Pure `sys.argv` parsing, no `argparse` dependency

## 🚀 Quick Start

### Installation
```bash
pip install cliss
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

### Disable Colours
```python
# No colours in output
cli = CLI(name="myapp", colour=False)

# Or via environment variable
$ NO_COLOR=1 python myapp.py --help
```

## 📋 API Reference

### `CLI` class
```python
CLI(
    name="cli",
    description=None,
    version=None,
    colour=True,
)
```
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | `None` | Program name in help |
| `description` | `str` | `None` | Description in help |
| `version` | `str` | `None` | Adds `--version` flag |
| `usage` | `str` | `"{self.name} [COMMAND] [OPTIONS] [ARGS]..."` | Custom usage string |
| `colour` | `bool` | `True` | Enable/disable ANSI colours in output |

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
| `mode: str = None` | `--mode` (default: None) |

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
| Tool | Deps | Style | Parser |
|------|------|-------|--------|
| **cliss** | 0 | Decorators + type hints | `sys.argv` |
| Fire | 1 ([termcolor](https://pypi.org/project/termcolor/)) | Introspection | Custom |
| Click | 0 | Decorators | Custom |
| Typer (0.26.0+) | 0 | Type hints | `click` |

cliss = Fire's zero-bloat philosophy + Typer's type-driven design. Pure `sys.argv` parsing, custom help formatter with ANSI-colours.

### Why sys.argv instead of argparse?
Manual `sys.argv` parsing gives complete control over argument handling, removes dependency on `argparse` internals, and keeps the codebase minimal. The custom parser handles flags, positional arguments, bool pairs, and type coercion directly.

### Bool flags?
Automatic `--name`/`--no-name` mutually exclusive group. `store_true` by default, `store_false` if default is `True`.

### Async?
`async def` handlers auto-run with `asyncio.run()`. Sync functions returning coroutines also work. Disable with `simple=True` for pure sync scripts.

### Help customisation?
Full Cargo-style coloured help with `HelpTheme` configuration. Custom usage strings, examples sections, and per-command help registration via `Help.register_command_help()`. Disable colours with `colour=False` or `NO_COLOR` environment variable.

## 📄 License

MIT — see [LICENSE](LICENSE) file.

---

**Author:** [Fkernel653](https://github.com/Fkernel653)
**Repository:** [github.com/Fkernel653/cliss](https://github.com/Fkernel653/cliss)
**PyPI:** [pypi.org/project/cliss](https://pypi.org/project/cliss/)
