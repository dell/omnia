# omnia-auto

Reusable test automation utilities for Dell Omnia modules.

Provides formatting, host connectivity, Ansible playbook execution, file
synchronisation, credential management, validation execution, and HTML/JSON
test reporting. Runtime paths and consumer-specific behavior are configured
through `configure()`.

## Features

- **Formatting** — ANSI colors, Unicode symbols, structured `TestLogger`, session summary table
- **Host / Config** — YAML config loading, Ansible Vault credentials, testinfra host, `connection_params()`
- **Runner** — `run_playbook()` with live output streaming, timeout, SSH wrapping
- **Sync** — `clone_repo()` and `sync_files()` for local or SSH file transfer
- **Report** — `TestReport` for JSON and HTML test result generation
- **Credentials** — bounded stdin input and atomic Ansible Vault updates
- **Validation** — shared FVT, NFT, and UT command dispatch through `ValidationRunner`

## Requirements

- Python 3.9 or newer on Linux
- Git on the execution host for `clone_repo()`
- OpenSSH client (`ssh` and `scp`) for remote operation
- `rsync` for directory synchronization
- `sshpass` when password-based SSH is used; it is not needed for key-based SSH
- Bash on the execution host for playbook execution

The Python installation brings in `ansible-core`, PyYAML, pytest, and
pytest-testinfra. In particular, `ansible-core` supplies `ansible-playbook`
and `ansible-vault` locally. When playbooks execute on a remote target, that
target must provide `ansible-playbook` too.

Remote helpers use OpenSSH's normal `known_hosts` file. Their compatibility
default is `StrictHostKeyChecking=accept-new`: a first connection records the
host key and later key changes fail. For pre-provisioned environments, set
`ssh_opts` to `StrictHostKeyChecking=yes` and install the expected host key
before connecting. Custom SSH settings must use allowlisted `-o Name=value`
connection options; command-bearing options and host-key-verification bypasses
are rejected.

## Development setup

Use an isolated virtual environment:

```bash
cd test/plugins
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --editable '.[dev]'
```

## Build

```bash
# Build and validate the wheel and source distribution:
./build_wheel.sh

# Build, validate, and install into the active virtual environment:
./build_wheel.sh --install

# Clean build artifacts:
./build_wheel.sh --clean
```

The script does not install missing build tools automatically. Install the
`dev` extra first, as shown above. To build manually:

```bash
cd test/plugins/
python -m build
python -m twine check dist/*
```

Set `OMNIA_AUTO_PYTHON=/path/to/python` when the build should use an
interpreter other than `python3`.

## Install

```bash
# From the Omnia repository root after building locally:
python -m pip install test/plugins/dist/omnia_auto-1.0.0-py3-none-any.whl

# Force reinstall (after rebuilding):
python -m pip install --force-reinstall test/plugins/dist/omnia_auto-1.0.0-py3-none-any.whl
```

After an official package release, installation can use
`python -m pip install omnia-auto`. Do not assume that command is available
until a release has been published.

## Command-line interface

Installing the package provides both of these equivalent entry points:

```bash
omnia-auto --help
python -m omnia_auto --help
```

Sensitive credential values should be supplied through stdin. Do not place
them directly in command-line arguments:

```bash
credential-json-provider | \
  omnia-auto write-fields \
    --fields-stdin \
    --creds-path credentials.yml \
    --key-path credentials.key
```

Here, `credential-json-provider` represents an approved secret manager or CI
secret-injection step that writes one JSON object to stdout. Avoid literal
secrets in shell history, process arguments, environment variables, or logs.

## Documentation

The detailed guides are included in the source distribution under `docs/`;
they are documentation files, not importable Python packages.

| Document | Description |
|----------|-------------|
| `USAGE.md` | Quick reference for all functions |
| `docs/` | Detailed per-category guides with parameters and examples |

### Per-Category Guides

| Guide | What it covers |
|-------|---------------|
| `01_configuration.md` | `configure()`, `get_setting()` |
| `02_formatting.md` | `Colors`, `Symbols`, `TestLogger`, `log()`, session summary |
| `03_host_and_config.md` | Config loading, credentials, testinfra, `connection_params()` |
| `04_sync.md` | `clone_repo()`, `sync_files()` |
| `05_runner.md` | `run_playbook()` with wrapper pattern |
| `06_report.md` | `TestReport`, HTML/JSON reports |
| `07_full_example.md` | Complete working conftest.py and test file |
| `08_credentials.md` | Secure credential API and command-line usage |
| `09_validation_runner.md` | Shared FVT, NFT, and UT command dispatcher |

## Project Structure

```
test/plugins/
├── pyproject.toml                  # Package metadata and build config
├── setup.py                        # Backwards-compatible setup script
├── LICENSE                         # Apache License 2.0 text shipped in artifacts
├── build_wheel.sh                  # Build and metadata-validation script
├── MANIFEST.in                     # Source distribution manifest
├── README.md                       # This file
├── USAGE.md                        # Quick function reference
├── dist/                           # Generated wheel and source distribution
├── docs/                           # Detailed per-category usage guides
└── omnia_auto/                     # Python package (import omnia_auto)
    ├── __init__.py                 # Public API exports + __version__
    ├── py.typed                    # PEP 561 type-checking marker
    ├── functions/                  # Core functions and internal helpers
    │   └── _ssh_options.py         # Internal SSH option validation
    ├── vars/                       # configure(), get_setting()
    └── messages/                   # Log and assertion message templates
```
