# Test Automation — Design Document

**Version**: 1.0
**Audience**: All Omnia test automation developers
**Purpose**: Generic architecture, patterns, and conventions for building test modules against any Omnia domain

---

## 1. Overview

Each Omnia domain (e.g., `image_build_manager`, `repo_manager`, `provision`, `discovery`, `telemetry`) has a corresponding **test module** under `test/<domain_name>/` that provides Functional Verification Testing (FVT) for that domain's Ansible playbooks.

All test modules share the **`omnia-auto`** plugin package (`test/plugins/`), which provides common utilities for host connectivity, playbook execution, file synchronisation, formatting, and HTML/JSON report generation. Domain modules install this shared package as a local wheel and build domain-specific verification on top of it.

### Execution Mode

Tests run on a developer workstation or CI runner, connecting to the target OIM server over SSH (remote mode) or running directly on the same machine (local mode). No container runtime is required for the test framework itself.

### Validated Environment

| Component | Minimum Version | Validated Version |
|-----------|----------------|-------------------|
| **Python** | 3.12+ | 3.12.8 |
| **pytest** | 9.0+ | 9.1.1 |
| **pytest-testinfra** | 10.0+ | 10.0.0 |
| **ansible-core** | 2.15+ | 2.20.0 |
| **RHEL** (target) | 10.0+ | 10.0 |

### Design Goals

- **Zero hardcoded values** — all IPs, paths, and credentials from `test_config.yml` / `test_creds.yml`
- **Shared plugin** — common utilities in `test/plugins/omnia_auto/`, installed as a local wheel
- **Strict separation** — functions in `functions/`, constants in `vars/`, messages in `messages/`
- **Structured output** — `TestLogger` produces consistent `✓`/`✗` formatted results with TC IDs
- **HTML + JSON reports** — consolidated report across scenario runs with merge support
- **Remote + local** — tests run against a remote OIM server or locally on the same host

---

## 2. Module Directory Structure

Every domain test module MUST follow this layout. Replace `<domain_name>` with your domain (e.g., `repo_manager`, `provision`, `discovery`):

```
test/<domain_name>/
├── conftest.py                           # Session setup: omnia_auto.configure(), pytest hooks
├── pytest.ini                            # Pytest configuration
├── run_validation.sh                     # CLI runner (scenario, command, markers, suites)
├── setup_env.sh                          # One-time venv setup + tab-completion install
├── test_config.yml                       # Target server, dataset, sync, report settings
├── test_creds.yml                        # SSH credentials (auto-encrypted with Ansible Vault)
├── test_run_config.yml                   # Batch execution config (--config mode)
├── requirements.txt                      # Python deps + local omnia-auto wheel
├── .gitignore                            # Excludes .venv, __pycache__, reports, vault keys
│
├── datasets/                             # Test input data (one dir per dataset)
│   └── data_set_01/
│       ├── input/                        # Synced to target domain input path
│       │   ├── <domain_name>_config.yml  # Domain-specific input config
│       │   └── <domain_name>_credentials.yml  # Vault-encrypted credentials (if needed)
│       └── <upstream>_output/            # Synced to upstream domain output dir (if needed)
│           ├── <upstream>_status.yml     # Upstream domain contract
│           └── ...
│
├── library/                              # Domain-specific code
│   ├── __init__.py                       # Public API: re-exports from sub-packages
│   ├── functions/
│   │   ├── __init__.py                   # Re-exports omnia_auto + domain functions
│   │   ├── <domain_name>_func.py         # Domain-specific verification functions
│   │   ├── host_func.py                  # Sync functions (project, input, output)
│   │   └── validation_func.py            # Config validation (validate_all())
│   ├── vars/
│   │   ├── __init__.py
│   │   └── common_vars.py               # Domain identity, paths, CMDS dict, constants
│   └── messages/
│       ├── __init__.py
│       └── <domain_name>_msgs.py         # TEST_NAMES, LOG_MSGS, ASSERT_MSGS
│
├── fvt/                                  # Functional Verification Tests
│   ├── TEST_CASES.md                     # Complete test case registry
│   ├── __init__.py
│   ├── <scenario_1>/                     # One dir per playbook tag or logical phase
│   │   ├── test_playbook.py              # Deploy test (runs the playbook)
│   │   └── <suite>/test_<suite>.py       # Verification tests per component
│   ├── <scenario_2>/
│   │   └── ...
│   └── <domain_name>/                    # Full end-to-end scenario (no tags)
│       ├── test_playbook.py
│       └── <suite>/test_<suite>.py
│
└── ut/                                   # Unit tests (offline, no target needed)
    └── test_<unit>.py
```

### Architecture Flow

```
  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────┐
  │ run_validation│     │  conftest.py  │     │       Target Server          │
  │    .sh       │────>│  pytest hooks │────>│         (OIM)                │
  │              │     │  + fixtures   │     │                              │
  └──────┬───────┘     └──────┬───────┘     └──────────────────────────────┘
         │                    │                          ▲
         │                    │                          │ SSH / testinfra
         │                    ▼                          │
         │             ┌──────────────┐           ┌─────┴──────┐
         │             │  fvt/        │           │  library/   │
         │             │  test files  │──────────>│  functions/ │ (domain-specific)
         │             │              │           │  vars/      │
         │             └──────────────┘           │  messages/  │
         │                                        └─────┬──────┘
         │                                              │ imports
         │                                              ▼
         │                                        ┌────────────┐
         │                                        │ omnia_auto  │ (shared plugin)
         ▼                                        │ test/plugins│
  ┌──────────────┐     ┌──────────────┐           └────────────┘
  │ test_config  │     │ test_run     │
  │   .yml       │     │  _config.yml │
  │ (connection) │     │ (scenarios)  │
  └──────────────┘     └──────────────┘
```

---

## 3. The `omnia-auto` Plugin (`test/plugins/`)

### 3.1 Purpose

`omnia-auto` is a shared Python package providing all common test automation utilities.
Domain test modules install it from a pre-built wheel and import its functions, avoiding
code duplication across domains. **Always check `omnia_auto` for an existing function
before writing a new one.**

### 3.2 Package Structure

```
test/plugins/
├── omnia_auto/                     # Python package (import omnia_auto)
│   ├── __init__.py                 # Public API: configure(), all exports
│   ├── functions/
│   │   ├── formatting_func.py      # Colors, Symbols, TestLogger, log()
│   │   ├── host_func.py            # Config loading, credentials, testinfra host
│   │   ├── runner_func.py          # run_playbook() with live output streaming
│   │   ├── sync_func.py            # clone_repo(), sync_files()
│   │   ├── report_func.py          # TestReport class (JSON + HTML core logic)
│   │   └── report_html.py          # HTML/CSS/JS report generation
│   ├── vars/common_vars.py         # configure(), get_setting(), defaults
│   └── messages/runner_msgs.py     # Runner log and assertion templates
├── dist/
│   └── omnia_auto-1.0.0-py3-none-any.whl   # Pre-built wheel
├── pyproject.toml                  # Build config (flat layout)
├── README.md                       # Full API documentation
├── USAGE.md                        # Quick function reference
└── docs/                           # Detailed per-category guides
```

### 3.3 Key Functions Provided

| Category | Functions | Module |
|----------|-----------|--------|
| **Configuration** | `configure()`, `get_setting()`, `get_module_root()` | `vars/common_vars.py` |
| **Formatting** | `Colors`, `Symbols`, `TestLogger`, `log()`, `set_debug_mode()` | `functions/formatting_func.py` |
| **Summary** | `add_session_result()`, `print_summary_table()`, `get_test_output()` | `functions/formatting_func.py` |
| **Config Loading** | `load_test_config()`, `load_test_credentials()`, `encrypt_test_credentials()` | `functions/host_func.py` |
| **Host Connection** | `get_testinfra_host()`, `is_local_execution()`, `run_on_host()`, `connection_params()` | `functions/host_func.py` |
| **Remote Utils** | `read_remote_env()`, `ensure_remote_dir()`, `resolve_domain_input_path()` | `functions/host_func.py` |
| **Runner** | `run_playbook()` — live output streaming, timeout, SSH wrapping | `functions/runner_func.py` |
| **Sync** | `clone_repo()`, `sync_files()` — local or SSH file transfer | `functions/sync_func.py` |
| **Report** | `TestReport`, `set_current_report()`, `get_current_report()` | `functions/report_func.py` |
| **HTML** | `generate_html()` — full HTML report with dark/light theme, charts | `functions/report_html.py` |

### 3.4 How Domain Modules Integrate

**Step 1** — `requirements.txt` references the local wheel:

```
../plugins/dist/omnia_auto-1.0.0-py3-none-any.whl
```

**Step 2** — `conftest.py` calls `omnia_auto.configure()` at session start:

```python
import omnia_auto
omnia_auto.configure(
    module_root=_TEST_DIR,
    config_file="test_config.yml",
    credentials_file="test_creds.yml",
    credentials_key=".test_creds.key",
)
```

**Step 3** — `library/functions/__init__.py` re-exports `omnia_auto` and wraps domain specifics:

```python
# Re-export common functions so test files import from library.functions only
from omnia_auto import (
    TestLogger, Colors, Symbols, log,
    load_test_config, load_test_credentials,
    get_testinfra_host, run_on_host, is_local_execution,
    TestReport, get_current_report, set_current_report,
    run_playbook as _run_playbook,
)
from ..vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR

# Domain-specific wrapper — injects playbook name and workdir
def run_playbook(tag=None, **kwargs):
    return _run_playbook(
        playbook=kwargs.pop("playbook", PLAYBOOK_ENTRY_POINT),
        playbook_workdir=kwargs.pop("playbook_workdir", PLAYBOOK_WORKDIR),
        tag=tag, **kwargs,
    )

# Domain-specific verification functions
from .<domain_name>_func import (
    check_container_running,
    check_services_active,
    # ... all domain-specific checks
)
```

**Step 4** — Test files import ONLY from `library.functions` (never from `omnia_auto` directly):

```python
from library.functions import run_playbook, TestLogger
from library.messages import TEST_NAMES, ASSERT_MSGS

def test_some_scenario(host):
    tl = TestLogger(TEST_NAMES["scenario_name"], "TC_XX_001")
    result = run_playbook(tag="prepare", timeout=1800)
    tl.passed("Completed") if result["success"] else tl.failed(result["error"])
    assert result["success"], ASSERT_MSGS["scenario_failed"]
```

### 3.5 Future Enhancement — PyPI Publishing

Currently `omnia-auto` is distributed as a local wheel inside the monorepo.
A future enhancement is to publish it to **PyPI** (`pip install omnia-auto`),
enabling external consumers and CI pipelines to install it without cloning the
monorepo. The package already has the full PyPI-ready structure (`pyproject.toml`,
`MANIFEST.in`, `PUBLISHING.md`, `LICENSE`) and can be published with:

```bash
cd test/plugins/
python -m build
python -m twine upload dist/*
```

Until then, all domain modules use the relative path to the local wheel.

---

## 4. Configuration Design

Every domain test module uses three config files. The structure is the same across all domains.

### 4.1 `test_config.yml` — Non-Sensitive Settings

```yaml
# test_config.yml — Connection, sync, and report settings
# All fields are REQUIRED unless marked optional

# --- Target Server ---
oim_server_ip: ""                    # Target OIM server IP (empty = local mode)
oim_ssh_user: "root"                 # SSH user
oim_ssh_port: 22                     # SSH port

# --- Project ---
dataset: "data_set_01"               # Dataset directory name under datasets/
project_name: "project_default"      # Omnia project name on target
clone_path: "/root/omnia"            # Where omnia repo is cloned on target
shared_path: "/opt/omnia/<domain_name>"  # Domain state dir on target

# --- Sync ---
sync_<domain_name>_input: true       # Sync datasets/input/ to target
sync_output: false                   # Sync upstream output to target (if needed)

# --- Report ---
report_path: "/opt/omnia/reports"    # Where HTML/JSON reports are saved
report_name: "<domain_name>"         # Report file prefix
report_id: ""                        # Custom report ID for merging (optional)
```

### 4.2 `test_creds.yml` — Sensitive Credentials

```yaml
# test_creds.yml — Auto-encrypted with Ansible Vault on first run
# NEVER commit real passwords. Ship with empty values.

oim_password: ""                     # SSH password for oim_server_ip
```

On first `pytest` session, `conftest.py` calls `encrypt_test_credentials()` which:
1. Generates a random key file (`.test_creds.key`)
2. Encrypts `test_creds.yml` with `ansible-vault encrypt`
3. `.gitignore` excludes `.test_creds.key` — the vault key never enters git

### 4.3 `test_run_config.yml` — Batch Execution

```yaml
# test_run_config.yml — Used by run_validation.sh --config
# Each domain defines its own scenarios matching its playbook tags

scenarios:
  <scenario_1>:
    order: 1
    run: true
    suite: ""
    marker: "sanity"
  <scenario_2>:
    order: 2
    run: true
    suite: ""
    marker: "sanity"
  <domain_name>:             # Full end-to-end (no tag)
    order: 3
    run: true
    suite: ""
    marker: "sanity"
```

### 4.4 Configuration Validation (`validation_func.py`)

Each module implements `validate_all()` which runs at session startup:

| Check | Rule |
|-------|------|
| `oim_server_ip` | Non-empty or empty for local mode |
| `dataset` | Non-empty, `datasets/<value>/` directory exists |
| `project_name` | Non-empty string |
| `clone_path` | Absolute path starting with `/` |
| `shared_path` | Absolute path starting with `/` |
| `report_path` | Non-empty string |
| `report_name` | Non-empty string |
| Input files | `datasets/<dataset>/input/<domain_name>_config.yml` exists |

**No fallback defaults.** If any required field is missing, session startup fails immediately with `ConfigValidationError`.

---

## 5. conftest.py — Pytest Hooks

The `conftest.py` is the most critical file in each test module. It orchestrates the entire session lifecycle. Every domain module implements the same hooks.

### 5.1 Hooks Implemented

| Hook | Purpose |
|------|---------|
| `pytest_addoption` | Add `--marker` CLI option for custom marker expression |
| `pytest_configure` | Register domain-specific custom markers |
| `pytest_collection_modifyitems` | Filter tests by marker expression, sort by `@pytest.mark.order(n)` |
| `pytest_sessionstart` | Validate config, encrypt credentials, sync files, init TestReport |
| `pytest_runtest_makereport` | Capture test results + output for report and summary table |
| `pytest_sessionfinish` | Save HTML/JSON report, print summary table |
| `pytest_report_teststatus` | Suppress default pytest `.` `s` `F` characters |

### 5.2 Session Startup Flow (Generic Pattern)

```python
def pytest_sessionstart(session):
    # 1. Validate config — fail fast
    try:
        result = validate_all()
    except ConfigValidationError as exc:
        pytest.exit(str(exc), returncode=1)

    # 2. Encrypt credentials
    try:
        encrypt_test_credentials()
    except (ValueError, OSError):
        pass

    config = load_test_config()
    host = get_testinfra_host()

    # 3. Sync project to remote (if remote mode)
    if not is_local_execution():
        sync_project_to_remote(host)

    # 4. Sync dataset input files (domain-specific sync function)
    if config.get("sync_<domain_name>_input", False):
        sync_<domain_name>_input(host)

    # 5. Sync upstream output (if applicable)
    if config.get("sync_output", False):
        sync_<upstream>_output(host)

    # 6. Initialize TestReport
    report = TestReport(
        module_name="<domain_name>",
        report_path=str(config.get("report_path")),
        report_name=str(config.get("report_name")),
        server_ip=str(config.get("oim_server_ip", "localhost")),
        report_id=os.environ.get("REPORT_ID"),
    )
    set_current_report(report)
```

### 5.3 Test Result Capture (`pytest_runtest_makereport`)

This hook is identical across all domains:

```python
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    result = outcome.get_result()

    if result.when not in {"call", "setup"}:
        return
    if result.when == "setup" and not result.skipped:
        return

    status = "PASSED" if result.passed else ("SKIPPED" if result.skipped else "FAILED")

    # Extract TC ID from docstring: "TC_XX_001: ..."
    tc_id = ""
    doc = getattr(item.obj, "__doc__", "") or ""
    if doc.strip().startswith("TC_"):
        tc_id = doc.strip().split(":", 1)[0].strip()

    add_session_result(test_name=item.name, status=status,
                       duration=getattr(result, "duration", 0), tc_id=tc_id)

    report = get_current_report()
    if report:
        report.add_result({
            "test_name": item.name, "status": status,
            "duration": getattr(result, "duration", 0),
            "details": get_test_output(item.name) or "",
            "error": str(result.longrepr) if result.failed else "",
        })
```

### 5.4 Custom Markers

Each domain registers its own markers. Common markers used across domains:

| Marker | Purpose |
|--------|---------|
| `@pytest.mark.order(n)` | Test execution order (lower first) |
| `@pytest.mark.sanity` | Baseline verification (must-pass) |
| `@pytest.mark.functional` | Extended functional verification |
| `@pytest.mark.deploy` | Playbook deployment tests |

Domains may add their own markers (e.g., `x86_64`, `aarch64`, `gpu`, `k8s`).

### 5.5 Marker Expression Filtering

The `--marker` option supports three modes:

| Expression | Mode | Meaning | Example |
|-----------|------|---------|---------|
| `sanity` | Single | Only tests with that marker | `--marker sanity` |
| `x86_64+sanity` | AND | Tests with **both** markers | `--marker x86_64+sanity` |
| `x86_64,aarch64` | OR | Tests with **either** marker | `--marker x86_64,aarch64` |

### 5.6 Host Fixture

```python
@pytest.fixture(scope="session")
def host():
    """Testinfra host connected to the target server."""
    return get_testinfra_host()
```

---

## 6. Execution Flow

### 6.1 Entry Point: `run_validation.sh`

Every domain module has its own `run_validation.sh` with the same interface:

```
run_validation.sh <scenario> <command> [--marker <expr>] [--suite <name>]
                       │          │
                       │          ├── deploy  → run playbook + verify tests
                       │          ├── verify  → verify tests only (no deploy)
                       │          └── test    → deploy + verify (combined)
                       │
                       └── <scenario> maps to fvt/<scenario>/
```

**Examples:**

```bash
# Verify a scenario with sanity tests
run_validation <scenario> verify --marker sanity

# Deploy + verify the full end-to-end
run_validation <domain_name> test

# Verify specific suite within a scenario
run_validation <scenario> verify --suite <suite_name>

# Run all scenarios from config file
run_validation --config

# Tab completion
eval "$(./run_validation.sh --completion)"
```

### 6.2 Suite Filtering

`--suite <name>` restricts pytest to `fvt/<scenario>/<suite>/`. Each domain defines its own suites based on the components the playbook manages.

### 6.3 Playbook ↔ Test Scenario Mapping

Each domain maps its playbook tags to test scenario directories:

| Playbook Tag | Test Scenario | Deploy Command |
|-------------|---------------|----------------|
| `<tag_1>` | `fvt/<tag_1>/` | `ansible-playbook <domain_name>.yml --tags <tag_1>` |
| `<tag_2>` | `fvt/<tag_2>/` | `ansible-playbook <domain_name>.yml --tags <tag_2>` |
| *(no tag)* | `fvt/<domain_name>/` | `ansible-playbook <domain_name>.yml` |

---

## 7. Verification Functions

### 7.1 Return Dict Pattern

Every verification function MUST return a dict with this structure:

```python
def check_something(host, resource_name: str) -> Dict[str, Any]:
    """Check if a resource exists on the target host.

    Args:
        host: Testinfra host connection.
        resource_name: Name of the resource to check.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    cmd = CMDS["check_resource"].format(name=resource_name)
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {
            "success": False,
            "details": "",
            "error": f"Resource {resource_name} not found",
        }
    return {
        "success": True,
        "details": f"Resource {resource_name} is present",
        "error": "",
    }
```

### 7.2 Common Verification Categories

Domains typically need functions in these categories:

| Category | Example Functions | What They Check |
|----------|-------------------|-----------------|
| **Container** | `check_container_running(host, name)` | Podman/Docker container is running |
| **Service** | `check_services_active(host)` | Systemd services active |
| **Port** | `check_firewall_ports_open(host)` | Firewall ports open |
| **File** | `check_file_exists(host, path)` | Configuration/output files exist |
| **Status** | `check_build_status(host)` | Domain output reports success |
| **Cleanup** | `check_resources_removed(host)` | Resources removed after cleanup |

### 7.3 Centralized Shell Commands (`CMDS`)

All shell commands MUST be defined in `library/vars/common_vars.py` under the `CMDS` dictionary. Verification functions use `CMDS[key].format(...)` — **never inline shell strings**.

```python
CMDS = {
    "podman_ps_check": (
        "podman ps --format '{{.Names}}'"
        " --filter name=^{container}$ 2>/dev/null"
    ),
    "systemctl_is_active": "systemctl is-active {service} 2>/dev/null",
    "firewall_list_ports": "firewall-cmd --list-ports 2>/dev/null",
    "file_exists": "test -f {path} && echo exists",
    "cat_file": "cat {path} 2>/dev/null",
    # ... domain-specific commands
}
```

### 7.4 Domain Constants (`common_vars.py`)

Each domain defines its own constants:

```python
# Domain identity
DOMAIN_NAME = "<domain_name>"

# Playbook config
PLAYBOOK_ENTRY_POINT = "<domain_name>.yml"
PLAYBOOK_WORKDIR = "src/<domain_name>/playbooks"
PLAYBOOK_TAGS = ["validate", "prepare", "build", "cleanup"]

# Domain-specific constants (examples)
CONTAINER_NAMES = ["my-service"]
SYSTEMD_SERVICES = ["my-service.service"]
FIREWALL_PORTS = ["8080/tcp", "443/tcp"]
```

---

## 8. Test File Patterns

### 8.1 Deploy Test Pattern (`test_playbook.py`)

```python
import pytest
from library.functions import run_playbook, TestLogger
from library.messages import TEST_NAMES, ASSERT_MSGS

@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_scenario(host):
    """TC_XX_001: Deploy <domain_name> --tags <tag>."""
    tl = TestLogger(TEST_NAMES["deploy_scenario"], "TC_XX_001")
    result = run_playbook(tag="<tag>", timeout=3600)
    tl.passed("Playbook completed") if result["success"] else tl.failed(result["error"])
    assert result["success"], ASSERT_MSGS["deploy_failed"]
```

### 8.2 Verify Test Pattern

```python
import pytest
from library.functions import TestLogger, check_something
from library.messages import TEST_NAMES, ASSERT_MSGS
from library.vars import SOME_CONSTANT

@pytest.mark.sanity
@pytest.mark.order(1)
def test_verify_resource(host):
    """TC_XX_002: Verify resource is present after deployment."""
    tl = TestLogger(TEST_NAMES["verify_resource"], "TC_XX_002")
    result = check_something(host, SOME_CONSTANT)
    tl.passed(result["details"]) if result["success"] else tl.failed(result["error"])
    assert result["success"], ASSERT_MSGS["resource_missing"].format(name=SOME_CONSTANT)
```

### 8.3 Skip Pattern for Optional Features

```python
@pytest.mark.functional
@pytest.mark.order(5)
def test_optional_feature(host):
    """TC_XX_010: Verify optional feature."""
    tl = TestLogger(TEST_NAMES["optional_feature"], "TC_XX_010")
    result = check_optional(host)
    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])
    tl.passed(result["details"]) if result["success"] else tl.failed(result["error"])
    assert result["success"], ASSERT_MSGS["optional_missing"]
```

### 8.4 Test File Rules

1. **Every test function** has a docstring starting with `TC_XX_NNN:`.
2. **Every test function** creates a `TestLogger` with the test name and TC ID.
3. **Every test function** calls `tl.passed()` or `tl.failed()` — never print directly.
4. **Deploy tests** always have `@pytest.mark.order(0)` to run first in their scenario.
5. **Verify tests** have `@pytest.mark.order(n)` with `n >= 1`.
6. **No imports from `omnia_auto`** — always import from `library.functions`.
7. **No inline strings** — all test names and assert messages from `library.messages`.

---

## 9. Message Rules

### 9.1 Message File Structure (`<domain_name>_msgs.py`)

```python
# --- Test Names ---
TEST_NAMES = {
    "deploy_scenario": "Deploy <domain_name> --tags <tag>",
    "verify_resource": "Verify resource is present",
}

# --- Log Messages ---
LOG_MSGS = {
    "resource_found": "Resource '{name}' is present: {status}",
    "resource_missing": "Resource '{name}' not found",
}

# --- Assertion Messages ---
ASSERT_MSGS = {
    "deploy_failed": "Playbook execution failed for --tags <tag>",
    "resource_missing": "Expected resource '{name}' to be present",
}
```

### 9.2 Rules

1. **ALL test names** go in `TEST_NAMES` — never inline in test files.
2. **ALL log messages** go in `LOG_MSGS` — never inline in function files.
3. **ALL assertion messages** go in `ASSERT_MSGS` — never inline in test files.
4. Use `.format()` with named placeholders for dynamic content.
5. Keys use `snake_case` matching the test or function name.

---

## 10. Data Flow

### 10.1 Environment Variable Flow

The target server must have `omnia.sh --setup-venv` run first, which installs environment variables system-wide:

```
src/main/omnia.env                       (source config)
        │
        │  omnia.sh --setup-venv
        ▼
/etc/profile.d/omnia-env.sh              (system-wide env vars on target)
        │
        │  read_remote_env() reads these at runtime
        ▼
OMNIA_DATA_PATH=/opt/omnia               (used to resolve domain input/output paths)
OMNIA_PROJECT_NAME=project_default       (project namespace)
```

### 10.2 Input File Flow (Generic)

```
test/<domain_name>/datasets/<dataset>/input/
        │
        │  sync_<domain_name>_input() via conftest.py session startup
        ▼
<OMNIA_DATA_PATH>/<domain_name>/input/<project_name>/
        │   ├── <domain_name>_config.yml
        │   └── <domain_name>_credentials.yml
        │
        │  ansible-playbook <domain_name>.yml reads via include_vars
        ▼
<OMNIA_DATA_PATH>/<domain_name>/output/<project_name>/
        │   └── <domain_name>_status.yml (or similar output contract)
```

### 10.3 Upstream Contract Flow (If Applicable)

```
test/<domain_name>/datasets/<dataset>/<upstream>_output/
        │
        │  sync_<upstream>_output() via conftest.py session startup
        ▼
<OMNIA_DATA_PATH>/<upstream>/output/<project_name>/
        │   ├── <upstream>_status.yml       (upstream contract)
        │   └── ...                         (upstream artifacts)
```

---

## 11. Report Architecture

### 11.1 Report Generation Pipeline

```
pytest_sessionstart  → TestReport("<domain_name>", report_path, ...)
pytest_runtest_makereport → TestReport.add_result({test_name, status, duration, details, error})
pytest_sessionfinish → TestReport.save() → JSON + HTML
                     → print_summary_table() → console summary with pass/fail/skip counts
```

### 11.2 Report System Architecture

The report system is split into two modules in `omnia_auto`:

- **`report_func.py`** — `TestReport` class, result collection, JSON persistence, run merging
- **`report_html.py`** — HTML/CSS/JS generation, SVG donut charts, theme toggle, expandable items

### 11.3 HTML Report Features

- Dark/light theme toggle with persistent state
- SVG donut chart with pass rate percentage
- Scenario breakdown tables with pass/fail/skip counts
- Expandable test items with full output and error details
- Server info panel with KPI cards

### 11.4 Report Merging

Multiple scenario runs with the same `REPORT_ID` environment variable merge into one report:

```bash
export REPORT_ID="full_run_$(date +%Y%m%d)"
run_validation <scenario_1> test --marker sanity
run_validation <scenario_2> test --marker sanity
# Both runs appear in one HTML report
```

---

## 12. Connection Architecture

### 12.1 Remote Mode (`oim_server_ip` set)

```
Automation Runner → SSH → Target Server (OIM)
                                │
                                ├── testinfra host = ansible://oim_server
                                ├── run_playbook() = sshpass + ssh + ansible-playbook
                                ├── sync_files() = rsync over SSH
                                └── read_remote_env() = ssh + source /etc/omnia/omnia.env
```

### 12.2 Local Mode (`oim_server_ip` empty)

```
Same Machine
    ├── testinfra host = local://
    ├── run_playbook() = subprocess.Popen
    ├── sync_files() = cp / rsync (no SSH)
    └── read_remote_env() = source /etc/omnia/omnia.env
```

---

## 13. Security

- **Credentials**: `test_creds.yml` encrypted with Ansible Vault on first session
- **Dataset credentials**: `<domain_name>_credentials.yml` vault-encrypted in datasets
- **No secrets in code**: All credentials loaded via `load_test_credentials()`
- **No secrets in git**: `.gitignore` excludes vault key files (`.test_creds.key`)
- **SSH options**: `StrictHostKeyChecking=no`, `UserKnownHostsFile=/dev/null` for automation
- **Bandit**: All `shell=True` subprocess calls annotated with `# nosec B602`
- **Gitleaks**: No hardcoded IPs, passwords, or tokens in committed code

---

## 14. Extensibility

### Adding a New Domain Test Module

1. Create `test/<domain_name>/` following the structure in Section 2
2. Add `requirements.txt` with `../plugins/dist/omnia_auto-1.0.0-py3-none-any.whl`
3. Add `conftest.py` calling `omnia_auto.configure()` with domain-specific config files
4. Add `library/functions/__init__.py` re-exporting `omnia_auto` functions + domain wrappers
5. Add `library/vars/common_vars.py` with domain constants (`CMDS`, container names, ports, etc.)
6. Add `library/messages/<domain_name>_msgs.py` with `TEST_NAMES`, `LOG_MSGS`, `ASSERT_MSGS`
7. Add `fvt/` with scenario directories matching the domain's playbook tags
8. Add `fvt/TEST_CASES.md` documenting every test case
9. Add `datasets/` with input data for the domain
10. Add `run_validation.sh` and `setup_env.sh` (copy from an existing module, update paths)

### Adding a New Test Scenario

1. Create `fvt/<scenario_name>/` directory with `__init__.py`
2. Add `test_playbook.py` at scenario root with deploy test (`@pytest.mark.order(0)`)
3. Add `<suite>/test_<suite>.py` for verification tests
4. Add test names and messages to `<domain_name>_msgs.py`
5. Add scenario to `test_run_config.yml`
6. Update `fvt/TEST_CASES.md` with new TC IDs

### Adding a New Verification Function

1. Add function to `<domain_name>_func.py` (return `{success, details, error}` dict)
2. Add shell command to `CMDS` in `common_vars.py` (if needed)
3. Add messages to `<domain_name>_msgs.py` (`TEST_NAMES`, `LOG_MSGS`, `ASSERT_MSGS`)
4. Create test in appropriate `fvt/<scenario>/<suite>/` folder
5. Run `pylint` (≥ 8.8) and `bandit` (no High severity)
6. Update `fvt/TEST_CASES.md` with the new TC ID

### Rebuilding the `omnia-auto` Wheel

If you modify the shared plugin code in `test/plugins/omnia_auto/`:

```bash
cd test/plugins/
pylint omnia_auto/                  # Must score ≥ 8.8
bandit -r omnia_auto/ -ll -ii      # No High severity
rm -rf dist/ build/ *.egg-info
python -m build --wheel
# Reinstall in each domain venv
cd ../image_build_manager/
source .venv/bin/activate
pip install --force-reinstall ../plugins/dist/omnia_auto-1.0.0-py3-none-any.whl
```
