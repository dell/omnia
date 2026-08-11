# Test Automation — Design Document

**Version**: 2.0
**Audience**: All Omnia test automation developers
**Purpose**: Architecture, patterns, and conventions for building test modules against any Omnia domain
**Reference Implementation**: `test/image_build_manager/`

---

## 1. Overview

Each Omnia domain (e.g., `image_build_manager`, `repo_manager`, `provision`, `discovery`, `telemetry`) has a corresponding **test module** under `test/<domain_name>/` that provides Functional Verification Testing (FVT) for that domain's Ansible playbooks.

All test modules share the **`omnia-auto`** plugin package (`test/plugins/`), which provides common utilities for host connectivity, playbook execution, file synchronization, formatting, and HTML/JSON report generation. Domain modules install this shared package as a local wheel and build domain-specific verification on top of it.

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
- **Centralized test metadata** — TC IDs and titles in `TEST_CASES` dict, never hardcoded
- **Centralized commands** — all shell commands in `CMDS` dict with named placeholders
- **Structured output** — `TestLogger` produces consistent pass/fail formatted results with TC IDs
- **HTML + JSON reports** — consolidated report across scenario runs with merge support
- **Remote + local** — tests run against a remote OIM server or locally on the same host

---

## 2. Module Directory Structure

Every domain test module MUST follow this layout. Replace `<domain_name>` with your domain (e.g., `repo_manager`, `provision`, `discovery`):

```
test/<domain_name>/
├── conftest.py                           # Session setup: omnia_auto.configure(), pytest hooks
├── run_validation.sh                     # CLI runner (scenario, command, markers, suites)
├── setup_env.sh                          # One-time venv setup + tab-completion install
├── test_config.yml                       # Target server, dataset, sync, report settings
├── test_creds.yml                        # SSH credentials (auto-encrypted with Ansible Vault)
├── test_run_config.yml                   # Batch execution config (--config mode)
├── requirements.txt                      # Python deps + local omnia-auto wheel
├── .gitignore                            # Excludes .venv, __pycache__, reports, vault keys
│
├── datasets/                             # Test input data (one dir per dataset)
│   ├── data_set_01/
│   │   ├── input/                        # Synced to target domain input path
│   │   │   ├── <domain_name>_config.yml  # Domain-specific input config
│   │   │   └── <domain_name>_credentials.yml  # Vault-encrypted credentials (if needed)
│   │   └── <upstream>_output/            # Synced to upstream domain output dir (if needed)
│   └── generator/                        # Dataset generator tool (optional)
│       ├── generate_dataset.py
│       ├── profiles/                     # Variable profiles (YAML)
│       └── templates/                    # Jinja2 templates
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
│   │   ├── common_vars.py               # Domain identity, paths, CMDS dict, constants
│   │   └── test_case_vars.py            # TEST_CASES dict (TC IDs + titles)
│   └── messages/
│       ├── __init__.py
│       └── <domain_name>_msgs.py         # TEST_LOG_MSGS, TEST_ASSERT_MSGS
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
         │                    │                          ^
         │                    │                          │ SSH / testinfra
         │                    v                          │
         │             ┌──────────────┐           ┌─────┴──────┐
         │             │  fvt/        │           │  library/   │
         │             │  test files  │──────────>│  functions/ │ (domain-specific)
         │             │              │           │  vars/      │
         │             └──────────────┘           │  messages/  │
         │                                        └─────┬──────┘
         │                                              │ imports
         │                                              v
         │                                        ┌────────────┐
         │                                        │ omnia_auto  │ (shared plugin)
         v                                        │ test/plugins│
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
│   ├── vars/common_vars.py         # configure(), get_setting(), shared paths
│   └── ...
├── dist/                           # Pre-built wheel
│   └── omnia_auto-1.0.0-py3-none-any.whl
├── pyproject.toml                  # Build configuration
└── USAGE.md                        # API reference
```

### 3.3 Key Exports

| Category | Functions |
|----------|-----------|
| **Config** | `configure()`, `load_test_config()`, `load_test_credentials()`, `get_setting()` |
| **Host** | `get_testinfra_host()`, `is_local_execution()`, `run_on_host()`, `connection_params()` |
| **Remote utils** | `read_remote_env()`, `ensure_remote_dir()`, `resolve_domain_input_path()` |
| **Sync** | `sync_files()`, `clone_repo()` |
| **Runner** | `run_playbook()` with live output streaming and timeout |
| **Formatting** | `TestLogger`, `Colors`, `Symbols`, `log()`, `add_session_result()`, `print_summary_table()` |
| **Report** | `TestReport`, `set_current_report()`, `get_current_report()`, `get_test_output()`, `get_last_tc_id()` |
| **Security** | `encrypt_test_credentials()` |

### 3.4 Integration Pattern

**Step 1** — `conftest.py` calls `configure()` to register the module:

```python
import omnia_auto
omnia_auto.configure(
    module_root=_TEST_DIR,
    config_file="test_config.yml",
    credentials_file="test_creds.yml",
    credentials_key=".test_creds.key",
)
```

**Step 2** — `library/functions/__init__.py` imports from `omnia_auto` and wraps
`run_playbook()` with domain-specific defaults:

```python
from omnia_auto import (
    TestLogger, Colors, Symbols, log,
    load_test_config, load_test_credentials,
    get_testinfra_host, run_on_host, is_local_execution,
    run_playbook as _run_playbook,
)
from ..vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR

def run_playbook(tag=None, **kwargs):
    return _run_playbook(
        playbook=kwargs.pop("playbook", PLAYBOOK_ENTRY_POINT),
        playbook_workdir=kwargs.pop("playbook_workdir", PLAYBOOK_WORKDIR),
        tag=tag, **kwargs,
    )
```

**Step 3** — Test files import ONLY from `library.functions` (never from `omnia_auto` directly):

```python
from library.functions import run_playbook, TestLogger
from library.vars import TEST_CASES as TC
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT

def test_deploy_prepare(host):
    tc = TC["deploy_prepare"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_playbook(playbook=PLAYBOOK_ENTRY_POINT, tag="prepare")
    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]))
    assert result["success"], ASSERT["playbook_failed"].format(...)
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

# --- Target Server ---
oim_server_ip: ""                    # Target OIM server IP (empty = local mode)
oim_ssh_user: "root"                 # SSH user
oim_ssh_port: 22                     # SSH port

# --- Project ---
dataset: ""                          # Empty = use src/ files directly
project_name: "project_default"      # Omnia project name on target
clone_path: "/root/omnia"            # Where omnia repo is cloned on target
shared_path: "/opt/omnia/image_build_manager"  # Domain state dir on target

# --- Sync ---
sync_image_build_input: true         # Sync input files to target
sync_output: false                   # Sync upstream output to target (if needed)

# --- Report ---
report_path: "reports"               # Where HTML/JSON reports are saved
report_name: "image_build_test_report"  # Report file prefix
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

skip_on_failure: false

scenarios:
  cleanup:
    order: 1
    run: true
    suite: ""
    marker: "sanity"
  validate:
    order: 2
    run: true
    suite: ""
    marker: "sanity"
  prepare:
    order: 3
    run: true
    suite: ""
    marker: "sanity"
  build:
    order: 4
    run: true
    suite: ""
    marker: "x86_64"
  image_build_manager:
    order: 5
    run: true
    suite: ""
    marker: "sanity"
```

### 4.4 Configuration Validation (`validation_func.py`)

Each module implements `validate_all()` which runs at session startup:

| Check | Rule |
|-------|------|
| `oim_server_ip` | Non-empty or empty for local mode |
| `dataset` | Non-empty and `datasets/<value>/` directory exists, or empty for src/ mode |
| `project_name` | Non-empty string |
| `clone_path` | Absolute path starting with `/` |
| `report_path` | Non-empty string |
| `report_name` | Non-empty string |
| Input files | `datasets/<dataset>/input/<config>.yml` exists (when dataset is set) |
| Src files | `src/<domain_name>/input/<config>.yml` exists (when dataset is empty) |

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

### 5.2 Session Startup Flow

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

    # 3. Apply dataset overrides from env vars (--config mode)
    _apply_dataset_overrides(config)

    host = get_testinfra_host()

    # 4. Sync project to remote (if remote mode)
    if not is_local_execution():
        sync_project_to_remote(host)

    # 5. Sync dataset input files
    if config.get("sync_image_build_input", False):
        sync_image_build_input(host)

    # 6. Sync upstream output (if applicable)
    if config.get("sync_output", False):
        sync_repo_manager_output(host)

    # 7. Initialize TestReport
    report = TestReport(
        module_name=DOMAIN_NAME,
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
    rep = outcome.get_result()
    if rep.when == "call":
        report = get_current_report()
        if report:
            tc_id = get_last_tc_id() or _TC_ID_MAP.get(item.name, "")
            report.add_result({
                "test_name": item.name,
                "tc_id": tc_id,
                "status": "passed" if rep.passed else "failed" if rep.failed else "skipped",
                "duration": rep.duration,
                "output": get_test_output() or "",
            })
        # Capture for summary table
        add_session_result(item, rep, tc_id=tc_id)
```

### 5.4 Marker Expression Syntax

The `--marker` option supports three modes:

| Syntax | Mode | Example | Meaning |
|--------|------|---------|---------|
| `sanity` | Single | `--marker sanity` | Tests with `@pytest.mark.sanity` |
| `x86_64,aarch64` | OR | `--marker x86_64,aarch64` | Tests with **either** marker |
| `x86_64+sanity` | AND | `--marker x86_64+sanity` | Tests with **both** markers |

### 5.5 Custom Markers

| Marker | Description |
|--------|-------------|
| `order(n)` | Execution order (lower first, deploy = 0) |
| `x86_64` | Test applies to x86_64 architecture |
| `aarch64` | Test applies to aarch64 architecture |
| `sanity` | Baseline verification (must-pass) |
| `functional` | Extended functional verification |
| `deploy` | Playbook deployment tests |

---

## 6. Test Coverage — Source-to-Test Mapping

### 6.1 image_build_manager Example

The reference implementation maps each source role to test verification:

| Source Role | Playbook Tag | Test Scenario | What Tests Verify |
|-------------|-------------|---------------|-------------------|
| `validate_image_build_input` | validate | `fvt/validate/` | Input config exists, credentials present |
| `deploy_minio` | prepare | `fvt/prepare/container/` | MinIO container running, systemd active, S3 buckets |
| `deploy_registry` | prepare | `fvt/prepare/container/` | Registry container running, reachable via HTTP |
| `image_build_setup` | prepare | `fvt/prepare/container/` | s3cmd configured, firewall ports open |
| `build_os_images` | build | `fvt/build/s3/`, `fvt/build/registry/` | S3 images, registry images, build_status |
| `cleanup_build_artifacts` | cleanup | `fvt/cleanup/cleanup/` | Containers removed, services stopped, S3 cleaned |

### 6.2 Test Count Summary (image_build_manager)

| Scenario | Prefix | Test Count |
|----------|--------|------------|
| image_build_manager | TC_IB_ | 13 |
| validate | TC_VL_ | 3 |
| prepare | TC_PR_ | 8 |
| build | TC_BD_ | 6 |
| cleanup | TC_CL_ | 8 |
| **Total** | | **38** |

### 6.3 Unit Tests

Unit tests in `ut/` validate source Ansible modules offline (no target server needed):

| Test File | Source Module | What It Tests |
|-----------|--------------|---------------|
| `test_validate_image_build_config.py` | `plugins/modules/validate_image_build_config.py` | JSON schema validation |
| `test_functional_group_packages.py` | `plugins/modules/generate_functional_groups.py` | Functional group parsing |
| `test_standalone_independence.py` | Domain structure | Module can run independently |

---

## 7. Data Flow

### 7.1 Environment Variable Flow

The target server must have `omnia.sh -s` run first, which installs environment variables system-wide:

```
src/main/omnia.env                       (source config)
        │
        │  omnia.sh -s
        v
/etc/profile.d/omnia-env.sh              (system-wide env vars on target)
        │
        │  read_remote_env() reads these at runtime
        v
OMNIA_DATA_PATH=/opt/omnia               (used to resolve domain input/output paths)
OMNIA_PROJECT_NAME=project_default       (project namespace)
SYSTEM_ADMIN_NIC_IPV4=<ip>              (admin NIC IP for S3 + registry)
```

### 7.2 Input File Flow

#### Default Mode (`dataset: ""`) — Recommended

```
src/image_build_manager/input/
  ├── image_build_config.yml
  └── package_groups.yml
        │
        │  sync_image_build_input() via conftest.py
        v
<OMNIA_DATA_PATH>/image_build_manager/input/<project_name>/
        │
        │  ansible-playbook reads via include_vars
        v
<OMNIA_DATA_PATH>/image_build_manager/output/<project_name>/
        └── build_status.yml
```

#### Custom Dataset Mode (`dataset: "data_set_01"`)

```
test/image_build_manager/datasets/data_set_01/input/
  ├── image_build_config.yml
  ├── image_build_credentials.yml
  └── package_groups.yml
        │
        │  sync_image_build_input() via conftest.py
        v
<OMNIA_DATA_PATH>/image_build_manager/input/<project_name>/
```

### 7.3 Upstream Contract Flow

```
test/image_build_manager/datasets/<dataset>/repo_manager_output/
  └── repo_status.yml
        │
        │  sync_repo_manager_output() via conftest.py
        v
<OMNIA_DATA_PATH>/repo_manager/output/<project_name>/
        └── repo_status.yml              (upstream contract consumed by build phase)
```

---

## 8. Report Architecture

### 8.1 Report Generation Pipeline

```
pytest_sessionstart  -> TestReport(DOMAIN_NAME, report_path, ...)
pytest_runtest_makereport -> TestReport.add_result({test_name, tc_id, status, duration, output})
pytest_sessionfinish -> TestReport.save() -> JSON + HTML
                      -> print_summary_table() -> console summary with pass/fail/skip counts
```

### 8.2 Report System Architecture

The report system is split into two modules in `omnia_auto`:

- **`report_func.py`** — `TestReport` class, result collection, JSON persistence, run merging
- **`report_html.py`** — HTML/CSS/JS generation, SVG donut charts, theme toggle, expandable items

### 8.3 HTML Report Features

- Dark/light theme toggle with persistent state
- SVG donut chart with pass rate percentage
- Scenario breakdown tables with pass/fail/skip counts
- Expandable test items with full output and error details
- Server info panel with KPI cards

### 8.4 Report Merging

When running `./run_validation.sh --config`, each scenario generates its own report.
The final step merges all scenario reports into a single consolidated report:

```
run_validation.sh --config
  ├── scenario 1 -> report_1.json
  ├── scenario 2 -> report_2.json
  └── scenario 3 -> report_3.json
         │
         v  (TestReport.merge_runs())
  consolidated_report.json + .html
```

---

## 9. Test File Patterns

### 9.1 Deploy Test Pattern (`test_playbook.py`)

```python
import pytest
from library.functions import run_playbook, TestLogger, load_test_config
from library.vars import TEST_CASES as TC
from library.vars.common_vars import (
    PLAYBOOK_ENTRY_POINT, BUILD_LOG_PATH, SHARED_PATH,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT

@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_prepare(host):
    """Deploy image_build_manager --tags prepare."""
    tc = TC["deploy_prepare"]
    tl = TestLogger(tc["title"], tc["id"])
    result = run_playbook(playbook=PLAYBOOK_ENTRY_POINT, tag="prepare")

    if result["success"]:
        tl.passed(LOG["playbook_success"].format(duration=result["duration"]))
    else:
        tl.failed(
            LOG["playbook_failed"].format(rc=result["rc"], duration=result["duration"]),
            result.get("error", "See playbook output above"),
        )

    config = load_test_config()
    assert result["success"], ASSERT["playbook_failed"].format(
        playbook="image_build_manager.yml", tag="prepare",
        rc=result["rc"], duration=result["duration"],
        log_path=BUILD_LOG_PATH.format(
            shared_path=SHARED_PATH,
            project=config.get("project_name", "project_default"),
        ),
    )
```

### 9.2 Verify Test Pattern

```python
import pytest
from library.functions import TestLogger, check_container_running
from library.vars import TEST_CASES as TC
from library.vars.common_vars import REGISTRY_CONTAINER
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT

@pytest.mark.sanity
@pytest.mark.order(2)
def test_registry_after_prepare(host):
    """Verify registry container after prepare."""
    tc = TC["registry_container_running"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_container_running(host, REGISTRY_CONTAINER)

    if result["success"]:
        tl.passed(
            LOG["container_running"].format(container=REGISTRY_CONTAINER),
            result["status"],
        )
    else:
        tl.failed(
            LOG["container_not_running"].format(container=REGISTRY_CONTAINER),
            result.get("error", ""),
        )

    assert result["success"], ASSERT["container_not_running"].format(
        container=REGISTRY_CONTAINER, status=result["status"],
    )
```

### 9.3 Skip Pattern for Optional Features

```python
@pytest.mark.aarch64
@pytest.mark.order(5)
def test_s3_images_aarch64(host):
    """Verify aarch64 images pushed to S3."""
    tc = TC["s3_images_aarch64"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_s3_images(host, arch="aarch64")

    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(result["details"])
    else:
        tl.failed(result["error"])

    assert result["success"], ASSERT["s3_images_missing"].format(arch="aarch64")
```

### 9.4 Test File Rules

1. **Every test function** creates a `TestLogger` with TC ID and title from `TEST_CASES` dict.
2. **Every test function** calls `tl.passed()` or `tl.failed()` — never print directly.
3. **Deploy tests** always have `@pytest.mark.order(0)` to run first in their scenario.
4. **Verify tests** have `@pytest.mark.order(n)` with `n >= 1`.
5. **No imports from `omnia_auto`** — always import from `library.functions`.
6. **No inline strings** — all log and assert messages from `library.messages`.
7. **No hardcoded TC IDs** — always from `TEST_CASES["key"]["id"]`.

---

## 10. Message Architecture

### 10.1 Message File Structure (`<domain_name>_msgs.py`)

```python
# --- Log Messages ---
TEST_LOG_MSGS: Dict[str, str] = {
    "playbook_success": "Playbook completed in {duration}",
    "playbook_failed": "Playbook failed (rc={rc}) in {duration}",
    "container_running": "Container '{container}' is running",
    "container_not_running": "Container '{container}' not running",
    "storage_backend_minio": "MinIO-backed S3 storage is running",
}

# --- Assertion Messages ---
TEST_ASSERT_MSGS: Dict[str, str] = {
    "playbook_failed": (
        "Playbook {playbook} --tags {tag} failed (rc={rc}, duration={duration})\n"
        "HOW TO FIX:\n"
        "  1. Check logs at: {log_path}\n"
        "  2. Run manually on the target server\n"
    ),
    "container_not_running": (
        "Expected container '{container}' to be running, got '{status}'\n"
        "HOW TO FIX:\n"
        "  1. Run --tags prepare first\n"
        "  2. Check: podman ps -a --filter name={container}\n"
    ),
}
```

### 10.2 Rules

1. **ALL log messages** go in `TEST_LOG_MSGS` — never inline in function files.
2. **ALL assertion messages** go in `TEST_ASSERT_MSGS` — never inline in test files.
3. Use `.format()` with named placeholders for dynamic content.
4. Keys use `snake_case` matching the test or function name.
5. Assertion messages SHOULD include "HOW TO FIX" sections with actionable steps.

---

## 11. Dataset Generator Design

### 11.1 Purpose

The dataset generator creates custom test input configurations from Jinja2 templates
and YAML variable profiles. It is only needed when testing with non-default values
(different repo types, S3 providers, or build settings).

### 11.2 Architecture

```
generator/
├── generate_dataset.py          # CLI tool
├── profiles/                    # Variable profiles (YAML)
│   ├── defaults.yml             # Base profile — all shared values
│   └── internet.yml             # Override: public repo URLs
└── templates/                   # Jinja2 templates
    ├── input/
    │   ├── image_build_config.yml.j2
    │   ├── image_build_credentials.yml.j2
    │   └── package_groups.yml.j2
    └── repo_manager_output/
        ├── repo_status.yml.j2
        └── functional_group_packages.yml.j2
```

### 11.3 Merge Order

`defaults.yml` -> `<profile>.yml` -> `--var` CLI overrides

### 11.4 Modes

| Mode | Command | Description |
|------|---------|-------------|
| Template | `python generate_dataset.py my_ds defaults` | Render from templates + profile |
| From src | `python generate_dataset.py my_ds --from-src` | Copy directly from `src/` |

---

## 12. Extensibility — Adding a New Domain

To add test automation for a new domain (e.g., `provision`):

1. **Create directory**: `test/provision/` following the module structure (Section 2)
2. **Copy scaffolding** from `test/image_build_manager/`:
   - `conftest.py` (update `configure()` params and domain imports)
   - `setup_env.sh`, `run_validation.sh` (update domain references)
   - `test_config.yml`, `test_creds.yml`, `test_run_config.yml`
   - `.gitignore`, `requirements.txt`
3. **Create library structure**:
   - `library/vars/common_vars.py` — domain identity, CMDS dict, constants
   - `library/vars/test_case_vars.py` — TEST_CASES dict
   - `library/functions/<domain>_func.py` — verification functions
   - `library/messages/<domain>_msgs.py` — TEST_LOG_MSGS, TEST_ASSERT_MSGS
4. **Map source roles to tests**: read `src/<domain>/roles/`, identify resources, write tests
5. **Create FVT structure**: one directory per playbook tag, with `test_playbook.py` + suites
6. **Document**: `fvt/TEST_CASES.md`, `README.md`

### Key Customization Points

| File | What to Change |
|------|----------------|
| `common_vars.py` | `DOMAIN_NAME`, `PLAYBOOK_ENTRY_POINT`, `PLAYBOOK_WORKDIR`, `CMDS`, constants |
| `test_case_vars.py` | All `TEST_CASES` entries for the domain |
| `conftest.py` | `omnia_auto.configure()` params, sync function imports |
| `test_config.yml` | Sync flags (`sync_<domain>_input`), `shared_path` |
| `test_run_config.yml` | Scenario names matching playbook tags |

---

## 13. Monorepo Architecture Decisions

| Area | Design Choice | Rationale |
|------|---------------|-----------|
| **Code delivery** | `rsync` project to target | Faster than `git clone` on each run |
| **Config source** | Environment variables on target (`omnia.env`) | Consistent with production deployment |
| **Env var setup** | `omnia.sh -s` installs to `/etc/profile.d/` | System-wide availability |
| **Input sync dest** | `<OMNIA_DATA_PATH>/<domain>/input/<project>/` | Matches production path layout |
| **Playbook workdir** | `src/<domain>/playbooks/` | Galaxy collection structure |
| **Common utilities** | `omnia-auto` pip package (local wheel) | Code reuse across domains |
| **Test metadata** | `TEST_CASES` dict in `test_case_vars.py` | Single source of truth for TC IDs |
| **Shell commands** | `CMDS` dict in `common_vars.py` | Centralized, auditable, grep-able |
