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
from cliss import CLI

cli = CLI(name="todo", description="Task manager", version="1.0.0")

@cli.command()
def add(task: str, priority: int = 1, done: bool = False):
    """Add a task."""
    status = "✓" if done else "○"
    return f"[{status}] {task} (priority: {priority})"

cli.run()
```

## 📋 Commands & Features

### `@cli.command()` — Define commands from functions
```python
@cli.command()
def fetch(url: str, retries: int = 3):
    """Download from URL with retries"""
    return f"Fetched {url} (retries: {retries})"
```

### Type → CLI mapping

| Function signature | CLI argument |
|--------------------|---------------|
| `name: str` | Positional `name` |
| `count: int = 1` | `--count` (default: 1) |
| `verbose: bool = False` | `--verbose` / `--no-verbose` |
| `mode: str = None` | `--mode` (default: None) |

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

### Manual argument declaration
```python
from cliss import Argument

@cli.command()
def convert(
    input: str,
    output: str,
    format: Argument("--format", "-f", choices=["json", "csv"], default="json")
):
    return f"Converted {input} → {output}.{format}"
```

## 🎨 CLI Configuration

```python
cli = CLI(
    name="myapp",                      # Program name in help
    description="Does amazing things", # Description in help
    version="2.0.0",                   # Adds --version flag
    color=False,                       # Disable ANSI colours
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
