# omnia-auto

Reusable test automation utilities for Dell Omnia modules.

Provides formatting, host connectivity, Ansible playbook execution, file
synchronisation, and HTML/JSON test reporting — all configurable via
`configure()`, with no hardcoded values.

## Features

- **Formatting** — ANSI colors, Unicode symbols, structured `TestLogger`, session summary table
- **Host / Config** — YAML config loading, Ansible Vault credentials, testinfra host, `connection_params()`
- **Runner** — `run_playbook()` with live output streaming, timeout, SSH wrapping
- **Sync** — `clone_repo()` and `sync_files()` for local or SSH file transfer
- **Report** — `TestReport` for JSON and HTML test result generation

## Build

```bash
# Build the wheel (from test/plugins/):
./build_wheel.sh

# Build and install into the current venv:
./build_wheel.sh --install

# Clean build artifacts:
./build_wheel.sh --clean
```

Or manually:

```bash
cd test/plugins/
rm -rf dist/ build/ omnia_auto.egg-info/
python3 -m build --wheel
```

## Install

```bash
# From the omnia repository root:
pip install test/plugins/dist/omnia_auto-1.0.0-py3-none-any.whl

# Force reinstall (after rebuilding):
pip install --force-reinstall test/plugins/dist/omnia_auto-1.0.0-py3-none-any.whl
```

## Documentation

| Document | Description |
|----------|-------------|
| **[USAGE.md](USAGE.md)** | Quick reference for all functions |
| **[docs/](docs/)** | Detailed per-category guides with parameters and examples |

### Per-Category Guides

| Guide | What it covers |
|-------|---------------|
| [01_configuration.md](docs/01_configuration.md) | `configure()`, `get_setting()` |
| [02_formatting.md](docs/02_formatting.md) | `Colors`, `Symbols`, `TestLogger`, `log()`, session summary |
| [03_host_and_config.md](docs/03_host_and_config.md) | Config loading, credentials, testinfra, `connection_params()` |
| [04_sync.md](docs/04_sync.md) | `clone_repo()`, `sync_files()` |
| [05_runner.md](docs/05_runner.md) | `run_playbook()` with wrapper pattern |
| [06_report.md](docs/06_report.md) | `TestReport`, HTML/JSON reports |
| [07_full_example.md](docs/07_full_example.md) | Complete working conftest.py + test file |

## Project Structure

```
test/plugins/
├── pyproject.toml                  # Package metadata and build config
├── setup.py                        # Backwards-compatible setup script
├── build_wheel.sh                  # Build script (./build_wheel.sh --install)
├── MANIFEST.in                     # Source distribution manifest
├── README.md                       # This file
├── USAGE.md                        # Quick function reference
├── dist/                           # Pre-built wheel
│   └── omnia_auto-1.0.0-py3-none-any.whl
├── docs/                           # Detailed per-category usage guides
└── omnia_auto/                     # Python package (import omnia_auto)
    ├── __init__.py                 # Public API exports + __version__
    ├── py.typed                    # PEP 561 type-checking marker
    ├── functions/                  # Core function modules
    ├── vars/                       # configure(), get_setting()
    └── messages/                   # Log and assertion message templates
```
