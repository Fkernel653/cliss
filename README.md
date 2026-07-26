# cliss — Lightweight framework for building CLI applications

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![PyPI](https://img.shields.io/pypi/v/cliss.svg)](https://pypi.org/project/cliss/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS%20%7C%20windows-lightgrey)]()
[![Ruff](https://img.shields.io/badge/code%20style-ruff-261230?logo=ruff&logoColor=white)](https://docs.astral.sh/ruff/)

Write type-annotated Python functions, get a full CLI — automatic `--help`, validation, async support, and zero dependencies.

## 🚀 Quick Start
```bash
pip install cliss                    # Python 3.10+
```
```python
from cliss import Cliss

cli = Cliss(name="todo", description="Task manager", version="1.0.0")


@cli.command()
def add(task: str, priority: int = 1, done: bool = False):
    """Add a task."""
    status = "✓" if done else "○"
    return f"[{status}] {task} (priority: {priority})"


@cli.command()
def list_all():
    """Show all tasks."""
    return "Nothing yet!"


cli()
```

```bash
$ python todo.py add "Buy milk" --priority 2
[○] Buy milk (priority: 2)

$ python todo.py list-all
Nothing yet!

$ python todo.py --help
Usage: todo [COMMAND] [OPTIONS] [ARGS]...

Task manager

Commands:
  add           Add a task.
  list-all      Show all tasks.

Options:
  -V, --version Print version info and exit
  -h, --help    Print help
```

## 📋 Commands & Features

### `@cli.command()` — Define commands from functions
```python
@cli.command()
def fetch(url: str, retries: int = 3):
    """Download from URL with retries"""
    return f"Fetched {url} (retries: {retries})"
```

### `@cli.argument()` — Customize argument flags
Use `@cli.argument()` above `@cli.command()` to customize flags, help text, and behavior for individual parameters.

```python
@cli.argument("-v", "--verbose", help="Enable verbose output")
@cli.argument("-r", "--retries", type=int, help="Number of retries")
@cli.command()
def fetch(url: str, verbose: bool = False, retries: int = 3):
    """Download from URL"""
    return f"Fetched {url} (retries: {retries})"
```

### Type → CLI mapping

| Function signature | CLI argument |
|--------------------|---------------|
| `name: str` | Positional `name` |
| `count: int = 1` | `--count` (default: 1) |
| `verbose: bool = False` | `--verbose` / `--no-verbose` |
| `mode: str = None` | `--mode` (default: None) |

### Boolean flag behavior

| Function signature | Help display | Usage |
|--------------------|--------------|-------|
| `flag: bool` | `--flag, --no-flag` (required) | `--flag` or `--no-flag` |
| `flag: bool = False` | `--flag` (default: disabled) | `--flag` enables, `--no-flag` also works |
| `flag: bool = True` | `--no-flag` (default: enabled) | `--no-flag` disables, `--flag` also works |

### Command groups
```python
remote = cli.group("remote", "Manage remotes")


@remote.command()
def add(name: str, url: str):
    return f"Added remote {name}"
```

### Async support
```python
@cli.command()
async def fetch(url: str, retries: int = 3):
    return f"Fetched {url} (retries: {retries})"
```

## 🎨 CLI Configuration

```python
cli = Cliss(
    name="myapp",  # Program name in help
    description="Does amazing things",  # Description in help
    version="2.0.0",  # Adds --version flag
    color=False,  # Disable ANSI colours
)
```

| Option | Description |
|--------|-------------|
| `name` | Program name in help |
| `description` | Description in help |
| `version` | Adds `--version` flag |
| `usage` | Custom usage string |
| `color` | Enable/disable ANSI colours (default: True) |

### Disable colours via environment
```bash
NO_COLOR=1 python myapp.py --help
```

## 📄 License & Acknowledgments

MIT License — Built with pure Python standard library:

| Module | Purpose |
|--------|---------|
| `sys` | Argument parsing |
| `asyncio` | Async command execution |
| `inspect` | Signature introspection |

**Author:** [Fkernel653](https://github.com/Fkernel653)
**Project:** [GitHub](https://github.com/Fkernel653/cliss) • [PyPI](https://pypi.org/project/cliss/)
