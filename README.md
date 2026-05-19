# cliss — A lightweight framework for building CLI applications on top of argparse

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
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
- **🎨 Coloured Help** — Automatic coloured output on Python 3.14+, ANSI fallback for older versions
- **🔧 argparse Access** — Full access to underlying parsers for advanced use

## 🚀 Quick Start

### Prerequisites
- Python 3.10+

### Installation

#### Via pip (recommended)
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
git clone https://github.com/Fkernel653/cliss.git && cd cliss
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

cli = CLI(
    name="todo",
    description="A simple task manager",
    version="1.0.0"
)

@cli.command()
def add(task: str, priority: int = 1, done: bool = False):
    """Add a new task to the list."""
    status = "✓" if done else "○"
    return f"[{status}] {task} (priority: {priority})"

@cli.command()
def list(filter: str = "all"):
    """List tasks. Use --filter to show pending/completed."""
    return f"Showing {filter} tasks"

if __name__ == "__main__":
    cli.run()
```

```bash
$ python todo.py add "Buy milk" --priority 2
[○] Buy milk (priority: 2)

$ python todo.py add "Call mom" --done --priority 3
[✓] Call mom (priority: 3)

$ python todo.py list --filter pending
Showing pending tasks

$ python todo.py --help
usage: todo [-h] [--version] {add,list} ...

A simple task manager

positional arguments:
  {add,list}   Commands
    add        Add a new task to the list.
    list       List tasks. Use --filter to show pending/completed.

options:
  -h, --help   show this help message and exit
  --version    show program's version number and exit
```

## 📋 Commands

### `CLI` class
```python
CLI(
    name="myapp",
    description="My CLI application",
    version="1.0.0",
    auto_help=True,
    colour=True
)
```
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `Optional[str]` | `None` | Program name in help output |
| `description` | `Optional[str]` | `None` | Description in help output |
| `version` | `Optional[str]` | `None` | Adds `--version` flag |
| `auto_help` | `bool` | `True` | Adds `--help` flag |
| `colour` | `bool` | `True` | Enables coloured help output (Python 3.14+ native, else ANSI) |

### `Argument` class
```python
from cliss import Argument

Argument(
    "--output", "-o",
    type=str,
    default=None,
    help="Output file path",
    required=False,
    choices=["json", "csv"],
    action="store_true"
)
```
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `*flags` | `str` | — | Argument flags (e.g., `--output`, `-o`) |
| `type` | `type` | `str` | Value type for coercion |
| `default` | `Any` | `None` | Default value |
| `help` | `str` | `""` | Help text |
| `required` | `bool` | `False` | Make argument required |
| `choices` | `Optional[List[Any]]` | `None` | Restrict allowed values |
| `action` | `Optional[str]` | `None` | argparse action (`store_true`, `store_false`, etc.) |

### Type → CLI Mapping
| Function Signature | CLI Argument | Behaviour |
|--------------------|--------------|-----------|
| `name: str` | Positional `name` | Required positional argument |
| `count: int = 1` | `--count` | Optional with type `int`, default `1` |
| `verbose: bool = False` | `--verbose` | Flag, `store_true` |
| `quiet: bool = True` | `--quiet` | Flag, `store_false` |
| `items: list[str]` | Positional `items` | Positional with type `str` |
| `mode: Optional[str] = None` | `--mode` | Optional with default `None` |

## 📖 Examples

### CRUD Application
```python
from cliss import CLI

cli = CLI(name="db", description="Simple key-value store")
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

if __name__ == "__main__":
    cli.run()
```

```bash
$ python db.py set name Alice
OK: name = Alice

$ python db.py get name
Alice

$ python db.py delete name
Deleted: name

$ python db.py delete missing --force
Deleted: missing
```

### Explicit Arguments with Choices
```python
from cliss import CLI, Argument

cli = CLI(name="convert", description="File format converter")

@cli.command(arguments=[
    Argument("input", help="Input file path"),
    Argument("--output", "-o", default="out.txt", help="Output file"),
    Argument("--format", "-f", choices=["json", "csv", "yaml"], default="json")
])
def convert(input: str, output: str = "out.txt", format: str = "json"):
    """Convert between file formats."""
    return f"Converting {input} -> {output} as {format}"

if __name__ == "__main__":
    cli.run()
```

```bash
$ python convert.py data.csv -o data.json -f json
Converting data.csv -> data.json as json

$ python convert.py data.csv -f xml
error: argument --format/-f: invalid choice: 'xml' (choose from 'json', 'csv', 'yaml')
```

### Async Command Handlers
```python
import asyncio
from cliss import CLI

cli = CLI(name="fetcher", description="Async data fetcher")

@cli.command()
async def fetch(url: str, retries: int = 3, timeout: float = 10.0):
    """Fetch data from URL asynchronously."""
    for attempt in range(retries):
        try:
            # Simulate async network request
            await asyncio.sleep(0.5)
            return f"Success: {url} (attempt {attempt + 1})"
        except Exception:
            if attempt == retries - 1:
                return f"Failed after {retries} attempts"
    return "Unknown error"

@cli.command()
async def parallel(urls: str, max_concurrent: int = 3):
    """Process multiple URLs in parallel."""
    url_list = urls.split(",")
    # Simulate parallel processing
    await asyncio.sleep(1)
    return f"Processed {len(url_list)} URLs with {max_concurrent} workers"

if __name__ == "__main__":
    cli.run()
```

### Global Arguments
```python
from cliss import CLI

cli = CLI(name="myapp", description="App with global flags")
cli.add_global_argument("--verbose", "-v", action="store_true", help="Verbose output")
cli.add_global_argument("--config", "-c", default="config.json", help="Config file")

@cli.command()
def status(verbose: bool = False):
    """Show application status."""
    return "Detailed status..." if verbose else "OK"

@cli.command()
def process(file: str, config: str = "config.json"):
    """Process a file with given config."""
    return f"Processing {file} with {config}"

if __name__ == "__main__":
    cli.run()
```

```bash
$ myapp status
OK

$ myapp --verbose status
Detailed status...

$ myapp --config prod.json process data.csv
Processing data.csv with prod.json
```

### Mixing Explicit and Inferred Arguments
```python
from cliss import CLI, Argument

cli = CLI(name="backup", description="Backup utility")

@cli.command(arguments=[
    Argument("--compress", "-z", action="store_true", help="Enable compression")
])
def backup(source: str, destination: str = "/backups", compress: bool = False):
    """Backup source directory to destination."""
    mode = "compressed" if compress else "uncompressed"
    return f"Backing up {source} -> {destination} ({mode})"

if __name__ == "__main__":
    cli.run()
```

```bash
$ python backup.py /home/user --compress
Backing up /home/user -> /backups (compressed)

$ python backup.py /var/www --destination /mnt/nas
Backing up /var/www -> /mnt/nas (uncompressed)
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
| Python 3.10+ | Type hints, `inspect.signature` |

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

Yes. `cli.parser` and `cli.subparsers` are standard argparse objects. Add custom actions, mutually exclusive groups, or parent parsers as needed:

```python
cli = CLI(name="myapp")

# Access the underlying argparse parser
group = cli.subparsers.add_parser("admin", help="Admin commands")
admin_sub = group.add_subparsers(dest="admin_command")

@cli.command(name="admin:users")
def list_users(role: str = "all"):
    """List users by role."""
    return f"Listing {role} users"
```

### Does it support nested commands?

For subcommand groups, access `cli.subparsers` directly or use dotted command names:

```python
@cli.command(name="compute:start")
def start(instance: str):
    return f"Starting {instance}"

@cli.command(name="compute:stop")
def stop(instance: str, force: bool = False):
    action = "Force stopping" if force else "Stopping"
    return f"{action} {instance}"
```

### How does async work?

If the command handler is `async def` or returns a coroutine, cliss automatically runs it with `asyncio.run()`. No manual event loop setup needed:

```python
@cli.command()
async def fetch(url: str):
    return f"Fetched {url}"

# Also works with sync functions returning coroutines
@cli.command()
def fetch_sync(url: str):
    async def _fetch():
        return f"Fetched {url}"
    return _fetch()
```

### How does coloured output work?

On **Python 3.14+**, cliss uses argparse's native `color=True` for automatic terminal-aware highlighting. On older versions, it falls back to `RawDescriptionHelpFormatter` for manual ANSI codes. Set `colour=False` to disable all colours.

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| **Arguments not appearing** | Check that explicit `Argument` objects' `dest` matches parameter names |
| **Bool flag inverted** | `bool = False` → `store_true`, `bool = True` → `store_false` |
| **Type coercion fails** | argparse error message shown automatically |
| **Subcommand not found** | Verify command name: `func.__name__` with `_` → `-` unless overridden |
| **Async handler not awaited** | Ensure function is `async def` or returns a coroutine object |
| **Colours not showing** | Requires Python 3.12+ for native colours, or TTY for ANSI fallback. Set `colour=False` to disable |

## 📄 License

MIT License — see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- [argparse](https://docs.python.org/3/library/argparse.html) — The foundation this is built on

---

**Author:** [Fkernel653](https://github.com/Fkernel653)
**Repository:** [github.com/Fkernel653/cliss](https://github.com/Fkernel653/cliss)
**PyPI:** [pypi.org/project/cliss](https://pypi.org/project/cliss/)
