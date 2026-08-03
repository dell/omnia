# omnia-auto

[![PyPI version](https://img.shields.io/badge/pypi-v1.0.0-blue)](https://pypi.org/project/omnia-auto/)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Typed](https://img.shields.io/badge/typing-typed-green)](https://peps.python.org/pep-0561/)

Reusable test automation utilities for [Dell Omnia](https://github.com/dell/omnia) modules.

Provides formatting, host connectivity, Ansible playbook execution, file synchronisation, and HTML/JSON test reporting — all configurable by the consumer via `configure()`, with no hardcoded values.

## Features

- **Formatting** — ANSI colors, Unicode symbols, structured `TestLogger`, session summary table
- **Host / Config** — YAML config loading, Ansible Vault credentials, testinfra host, `connection_params()`, `read_remote_env()`, `ensure_remote_dir()`, `resolve_domain_input_path()`
- **Runner** — `run_playbook()` with live output streaming, timeout, SSH wrapping
- **Sync** — `clone_repo()` and `sync_files()` for local or SSH file transfer
- **Report** — `TestReport` for JSON and HTML test result generation

## Installation

### From PyPI

```bash
pip install omnia-auto
```

### From wheel (internal distribution)

```bash
pip install omnia_auto-1.0.0-py3-none-any.whl
```

### From Git

```bash
pip install git+https://github.com/balajikumaran-c-s/omnia-auto.git@v1.0.0
```

### From source (editable / development)

```bash
git clone https://github.com/balajikumaran-c-s/omnia-auto.git
cd omnia-auto
pip install -e ".[dev]"
```

## Quick Start

```python
import os
import omnia_auto

# 1. Configure (once, at startup)
omnia_auto.configure(
    module_root=os.path.dirname(__file__),
    config_file="test_config.yml",
    credentials_file="test_creds.yml",
    credentials_key=".test_creds.key",
    default_timeout=3600,
)

# 2. Import and use any function
from omnia_auto import (
    TestLogger, load_test_config, get_testinfra_host,
    connection_params, sync_files, clone_repo,
    run_playbook, TestReport, set_current_report,
)

tl = TestLogger("Verify module deployment", "TC_001")
tl.check("Loading configuration...")
config = load_test_config()
tl.passed(f"Config loaded for {config.get('project_name')}")

# 3. Run a playbook
result = run_playbook(
    playbook="image_build_manager.yml",
    playbook_workdir="src/image_build_manager/playbooks",
    tag="prepare",
    timeout=1800,
)
assert result["success"], result["error"]
```

## Documentation

| Document | Description |
|----------|-------------|
| **[USAGE.md](USAGE.md)** | Quick reference for all functions |
| **[docs/](docs/)** | Detailed per-category guides with parameters, prerequisites, and examples |
| **[PUBLISHING.md](PUBLISHING.md)** | How to build, verify, and upload to PyPI |
| **[CHANGELOG.md](CHANGELOG.md)** | Version history and release notes |
| **[CONTRIBUTING.md](CONTRIBUTING.md)** | Coding standards, pylint rules, security checks, PR checklist |

### Per-Category Guides

| Guide | What it covers |
|-------|---------------|
| [01_configuration.md](docs/01_configuration.md) | `configure()`, `get_setting()` |
| [02_formatting.md](docs/02_formatting.md) | `Colors`, `Symbols`, `TestLogger`, `log()`, session summary |
| [03_host_and_config.md](docs/03_host_and_config.md) | Config loading, credentials, testinfra, `connection_params()`, remote utils |
| [04_sync.md](docs/04_sync.md) | `clone_repo()`, `sync_files()` |
| [05_runner.md](docs/05_runner.md) | `run_playbook()` with wrapper pattern |
| [06_report.md](docs/06_report.md) | `TestReport`, HTML/JSON reports |
| [07_full_example.md](docs/07_full_example.md) | Complete working conftest.py + test file |

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full coding standards, pylint requirements
(score ≥ 8.8), security rules, and PR checklist.

1. **Fork** the repository
2. **Create a branch** — `git checkout -b feature/my-change`
3. **Make changes** and test — pylint score must stay ≥ 8.8
4. **Security scan** — no hardcoded IPs, passwords, or tokens
5. **Build** — `python -m build && python -m twine check dist/*`
6. **Commit** — `git commit -s -m "feat: description"` (use `--signoff`)
7. **Push** — `git push origin feature/my-change`
8. **Open a Pull Request**

### Building and publishing

See **[PUBLISHING.md](PUBLISHING.md)** for the full guide. Quick summary:

```bash
rm -rf dist/ build/ src/*.egg-info
python -m build
python -m twine check dist/*
python -m twine upload dist/*
```

## Project Structure

```
omnia-auto/
├── pyproject.toml                  # Package metadata and build config
├── MANIFEST.in                     # Source distribution manifest
├── README.md                       # This file (shown on PyPI)
├── USAGE.md                        # Quick function reference
├── CHANGELOG.md                    # Version history
├── PUBLISHING.md                   # PyPI publishing guide
├── CONTRIBUTING.md                 # Coding standards, pylint, security rules
├── LICENSE                         # Apache 2.0
├── docs/                           # Detailed per-category usage guides
│   ├── 01_configuration.md
│   ├── 02_formatting.md
│   ├── 03_host_and_config.md
│   ├── 04_sync.md
│   ├── 05_runner.md
│   ├── 06_report.md
│   └── 07_full_example.md
└── src/omnia_auto/
    ├── __init__.py                 # Public API exports + __version__
    ├── py.typed                    # PEP 561 type-checking marker
    ├── functions/
    │   ├── formatting_func.py      # Colors, Symbols, TestLogger, log()
    │   ├── host_func.py            # Config, credentials, testinfra, connection_params
    │   ├── report_func.py          # TestReport (JSON + interactive HTML)
    │   ├── runner_func.py          # run_playbook() with live streaming
    │   └── sync_func.py            # clone_repo(), sync_files()
    ├── vars/
    │   └── common_vars.py          # configure(), get_setting()
    └── messages/
        └── runner_msgs.py          # Log and assertion message templates
```

## License

Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
