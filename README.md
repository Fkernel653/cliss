# cliss — A lightweight framework for building CLI applications on top of argparse

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![PyPI](https://img.shields.io/pypi/v/cliss.svg)](https://pypi.org/project/cliss/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS%20%7C%20windows-lightgrey)]()
[![Ruff](https://img.shields.io/badge/code%20style-ruff-261230?logo=ruff&logoColor=white)](https://docs.astral.sh/ruff/)

Write type-annotated Python functions, get a full CLI — automatic `--help`, validation, and async support with zero dependencies.

## ✨ Features

- **🪶 Zero Dependencies** — Pure stdlib: `argparse`, `asyncio`, `inspect`
- **🏷️ Type-Driven** — Automatic arguments from function signatures and type hints
- **🧩 Flexible** — Declarative `Argument` objects, type inference, or both
- **⚡ Async-Native** — `async def` handlers with automatic event loop management
- **🌍 Global Args** — Define flags shared across all commands
- **🔧 argparse Access** — Full access to underlying parsers for advanced use

## 🚀 Quick Start

### Prerequisites
- Python 3.9+

### Installation
```bash
pip install cliss
```

#### Via uv
```bash
uv pip install cliss
```

#### Via pipx (isolated environment)
```bash
pipx install cliss
```

#### From source (development)

```bash
git clone https://github.com/yourusername/cliss.git && cd cliss
```

**pip**
```bash
pip install .
```

**uv**
```bash
uv pip install .
```
**pipx**
```bash
pipx install .
```

### Usage
```python
from cliss import CLI

cli = CLI(name="todo", description="Task manager", version="1.0.0")

@cli.command()
def add(task: str, priority: int = 1, done: bool = False):
    """Add a new task."""
    status = "✓" if done else "○"
    return f"[{status}] {task} (priority: {priority})"

if __name__ == "__main__":
    cli.run()
```

```bash
$ python todo.py add "Buy milk" --priority 2
[○] Buy milk (priority: 2)
$ python todo.py add "Call mom" --done --priority 3
[✓] Call mom (priority: 3)
```

## 📋 Commands

### `CLI` class
```python
CLI(name="myapp", description="...", version="1.0.0", auto_help=True)
```
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | — | Program name in help output |
| `description` | `str` | — | Description in help output |
| `version` | `str` | — | Adds `--version` flag |
| `auto_help` | `bool` | `True` | Adds `--help` flag |

### `Argument` class
```python
Argument("--output", "-o", type=str, default=None, help="...", required=False, choices=["a","b"], action="store_true")
```
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `*flags` | `str` | — | Argument flags (e.g., `--output`, `-o`) |
| `type` | `type` | `str` | Value type for coercion |
| `default` | `Any` | `None` | Default value |
| `help` | `str` | `""` | Help text |
| `required` | `bool` | `False` | Make argument required |
| `choices` | `list` | — | Restrict allowed values |
| `action` | `str` | — | argparse action (`store_true`, etc.) |

### Type → CLI Mapping
| Function Signature | CLI Argument |
|--------------------|--------------|
| `name: str` | Positional `name` |
| `count: int = 1` | `--count` with type `int`, default `1` |
| `verbose: bool = False` | `--verbose` flag (store_true) |
| `quiet: bool = True` | `--quiet` flag (store_false) |

## 📖 Examples

### CRUD Application
```python
from cliss import CLI

cli = CLI(name="db", description="Key-value store")
db = {}

@cli.command()
def set(key: str, value: str):
    """Store a value."""
    db[key] = value
    return f"OK: {key} = {value}"

@cli.command()
def get(key: str):
    """Retrieve a value."""
    return db.get(key, "Not found")

@cli.command()
def delete(key: str, force: bool = False):
    """Delete a key."""
    if force or key in db:
        db.pop(key, None)
        return f"Deleted: {key}"
    return f"Not found: {key} (use --force)"

cli.run()
```

### Explicit Arguments
```python
from cliss import CLI, Argument

cli = CLI(name="convert")

@cli.command(arguments=[
    Argument("input", help="Input file"),
    Argument("--output", "-o", default="out.txt"),
    Argument("--format", "-f", choices=["json", "csv"], default="json")
])
def convert(input: str, output: str = "out.txt", format: str = "json"):
    """Convert file format."""
    return f"{input} -> {output} [{format}]"
```

### Async Handler
```python
@cli.command()
async def fetch(url: str, retries: int = 3):
    """Fetch data asynchronously."""
    return f"Fetched {url} (retries: {retries})"
```

### Global Arguments
```python
cli = CLI(name="myapp")
cli.add_global_argument("--verbose", "-v", action="store_true")

@cli.command()
def status(verbose: bool = False):
    return "Detailed status..." if verbose else "OK"
```
```bash
$ myapp --verbose status
Detailed status...
```

## 📁 Project Structure
```
cliss/
├── cliss/
│   └── __init__.py      # CLI, Argument classes
├── pyproject.toml       # Project metadata
├── README.md            # Documentation
└── LICENSE              # MIT License
```

## 🔧 Requirements

| Dependency | Purpose |
|------------|---------|
| Python 3.9+ | Type hints, `inspect.signature` |

No external dependencies — stdlib only.

## ❓ FAQ

### Why cliss when argparse already works?

argparse is powerful but verbose. A simple app with 3 commands can easily require 100+ lines of parser setup. cliss reduces this to type-annotated functions — the boilerplate is inferred, not written.

### What about Click/Typer/Fire?

| Tool | Dependencies | Style |
|------|-------------|-------|
| **cliss** | 0 (stdlib) | Decorators + type hints |
| Click | Click | Decorators |
| Typer | Click, typing-extensions | Type hints |
| Fire | 0 (stdlib) | Introspection |

cliss sits between Fire (zero-config, no validation) and Typer (rich features, heavy deps). It gives you type-driven CLI generation with argparse-compatible control, all in ~200 lines.

### Can I use argparse features directly?

Yes. `cli.parser` and `cli.subparsers` are standard argparse objects. Add custom actions, mutually exclusive groups, or parent parsers as needed.

### Does it support nested commands?

For subcommand groups, access `cli.subparsers` directly or use dotted command names:

```python
@cli.command(name="compute:start")
def start(instance: str):
    return f"Starting {instance}"
```

### How does async work?

If the command handler is `async def` or returns a coroutine, cliss automatically runs it with `asyncio.run()`. No manual event loop setup needed.

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| **Arguments not appearing** | Check that explicit `Argument` objects' `dest` matches parameter names |
| **Bool flag inverted** | `bool = False` → `store_true`, `bool = True` → `store_false` |
| **Type coercion fails** | argparse error message shown automatically |
| **Subcommand not found** | Verify command name: `func.__name__` with `_` → `-` unless overridden |

## 📄 License

MIT License — see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- [argparse](https://docs.python.org/3/library/argparse.html) — The foundation this is built on

---

**Author:** [Fkernel653](https://github.com/Fkernel653)
**Repository:** [github.com/Fkernel653/cliss](https://github.com/Fkernel653/cliss)
**PyPI:** [pypi.org/project/cliss](https://pypi.org/project/cliss/)
