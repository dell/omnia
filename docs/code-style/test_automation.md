# Test Automation — Coding Rules

> All test automation code under `test/` MUST follow these rules.
> These rules apply to every domain test module.

**Cross-references:**
- **Co-change rule** (code changes require test updates): see `general.md` §6
- **AI agent policy** (no AI sign-off): see `general.md` §7
- **Architecture and patterns**: see `docs/design/test-automation-design.md`

---

## 1. Pre-Development Analysis (MANDATORY)

### 1.1 Analyze the Source Code First

Before writing **any** automation code:

1. **Read the playbook source** under `src/<domain_name>/playbooks/` and `src/<domain_name>/roles/`.
2. **Identify all roles** the playbook calls, what hosts it targets, and what resources it creates (containers, services, files, pods, configs).
3. **Map each resource to a verification test** — every container the playbook creates should have a test that checks it is running, every service should be checked as active, etc.

```bash
# Example: analyze a domain
ls src/<domain_name>/playbooks/       # Main playbook entry points
ls src/<domain_name>/roles/           # All roles
cat src/<domain_name>/playbooks/<tag>/<tag>_<domain_name>.yml
```

### 1.2 Manually Verify on a Working Cluster

If a working cluster is available:

1. **Log into the target server** and manually verify the feature works.
2. **Check containers, services, ports, files** that the playbook creates.
3. **Document what you verified manually** — these become your test cases.
4. **Never automate blind** — if you have not verified it manually at least once, do not write automation for it.

### 1.3 Check `omnia-auto` Core Functions FIRST

Before writing ANY new function:

1. **Install `omnia-auto` from the local wheel**:
   ```bash
   pip install ../plugins/dist/omnia_auto-1.0.0-py3-none-any.whl
   python -c "import omnia_auto; print(omnia_auto.__all__)"
   ```
2. **Read the API reference**: `test/plugins/USAGE.md` and `test/plugins/docs/`
3. **Search for existing functions** — SSH connection, file sync, config loading, host connection, playbook execution, formatting, reporting are all provided by `omnia_auto`.
4. **Only write a new function if no existing `omnia_auto` function covers it.**
5. If your new function is generic enough to be reused across domains, propose adding it to `test/plugins/omnia_auto/` and rebuild the wheel.

**Core functions already provided by `omnia_auto`:**

| Instead of | Use |
|------------|-----|
| `host.run("ssh ...")` | `run_on_host(host, cmd)` |
| `host.run("rsync ...")` | `sync_files(mode="ssh", ...)` |
| `host.run("git clone ...")` | `clone_repo(mode="ssh", ...)` |
| `subprocess.run(["ansible-playbook", ...])` | `run_playbook(tag=..., timeout=...)` |
| `open("test_config.yml")` | `load_test_config()` |
| `open("test_creds.yml")` | `load_test_credentials()` |
| Inline color codes | `Colors.GREEN`, `Symbols.CHECK` |
| `print(...)` for test output | `log(msg, level)` or `TestLogger` |

---

## 2. Module Structure Rules

### 2.1 Directory Structure (MANDATORY)

Every domain test module must follow this structure:

```
test/<domain_name>/
├── conftest.py                    # Session setup, omnia_auto.configure()
├── test_config.yml                # Non-sensitive settings (IP, paths)
├── test_creds.yml                 # SSH + domain credentials (auto-encrypted)
├── requirements.txt               # Dependencies including omnia-auto wheel
├── run_validation.sh              # CLI runner
├── setup_env.sh                   # One-time venv + tab-completion setup
├── datasets/
│   ├── data_set_01/               # Generated via generator tool
│   │   └── input/                 # Synced to target
│   └── generator/                 # Dataset generator (MANDATORY)
│       ├── generate_dataset.py
│       ├── profiles/              # Variable profiles (YAML)
│       └── templates/             # Jinja2 templates
├── library/
│   ├── functions/
│   │   ├── __init__.py            # Public API — imports from omnia_auto + domain
│   │   ├── <domain_name>_func.py  # Domain-specific verification functions
│   │   ├── host_func.py           # Sync functions, re-exports from omnia_auto
│   │   └── validation_func.py     # Config validation
│   ├── vars/
│   │   ├── common_vars.py         # Constants (container names, paths, CMDS dict)
│   │   └── test_case_vars.py      # TEST_CASES dict (TC IDs + titles)
│   └── messages/
│       └── <domain_name>_msgs.py  # TEST_LOG_MSGS, TEST_ASSERT_MSGS
├── fvt/                           # Functional Verification Tests
│   ├── README.md                  # All FVT test cases documented
│   ├── <scenario>/                # One dir per playbook tag
│   │   ├── test_playbook.py       # Deploy test
│   │   └── <suite>/test_<suite>.py
│   └── <domain_name>/             # Full end-to-end (no tag)
└── nft/                           # Non-Functional Tests (optional)
    ├── README.md                  # NFT test cases and thresholds
    ├── test_performance.py        # Performance threshold tests
    └── test_idempotency.py        # Idempotency tests
```

### 2.2 Dataset and Input File Behavior

#### Dataset Generation (Recommended)

Datasets SHOULD be created using the dataset generator tool. The generator
ensures consistent structure, required files, and correct field values.

```bash
cd datasets/generator/

# Generate from a profile
python generate_dataset.py <dataset_name> <profile>

# Generate with variable overrides
python generate_dataset.py <dataset_name> <profile> --var key=value

# Copy from src/ (for quick bootstrap)
python generate_dataset.py <dataset_name> --from-src

# List available profiles
python generate_dataset.py --list-profiles
```

**Rules:**
- Every domain module MUST include a `datasets/generator/` directory
- Generator MUST have `defaults.yml` base profile and domain-specific profiles
- Generator MUST use Jinja2 templates under `templates/` for all config files
- Generated datasets MUST contain all required input files for the domain
- The `--from-src` mode copies from `src/<domain_name>/input/` and creates
  placeholder credentials — use this to bootstrap a new dataset quickly

#### Empty Dataset — Target Server Input (`dataset: ""`)

When `dataset` is empty (or not set), the playbook reads input files directly
from the **target server** at:

```
$OMNIA_DATA_PATH/<domain_name>/input/<project_name>/
```

In this mode, **no input files are synced** from the local machine. The files
must already exist on the target (e.g., placed there by a previous deployment
or manually). This is the **production behavior** — `omnia.sh` places config
files at this path during setup.

When `sync_<domain_name>_input: true` is set AND `dataset` is empty, the
framework syncs from `src/<domain_name>/input/` to the target path as a
convenience for development.

### 2.3 Strict Separation Rules

| Content | Location | Never In |
|---------|----------|----------|
| Shell commands | `CMDS` dict in `common_vars.py` | Test files, function files |
| TC IDs and titles | `TEST_CASES` dict in `test_case_vars.py` | Test files (hardcoded) |
| Log messages | `TEST_LOG_MSGS` in `<domain_name>_msgs.py` | Test files |
| Assert messages | `TEST_ASSERT_MSGS` in `<domain_name>_msgs.py` | Test files |
| Constants | `common_vars.py` | Function or test files |
| Verification logic | `functions/<domain_name>_func.py` | Test files |

### 2.4 `__init__.py` Requirements

Every `__init__.py` MUST:
1. Include Apache 2.0 license header (current year)
2. Provide a module docstring
3. Import and re-export specific items (no `import *`)
4. Group imports: functions, then vars, then messages

### 2.5 Re-exports with `__all__`

When importing from `omnia_auto` for re-export:

```python
from omnia_auto import (
    load_test_config,
    load_test_credentials,
    get_testinfra_host,
    run_on_host,
)

__all__ = [
    "load_test_config",
    "load_test_credentials",
    "get_testinfra_host",
    "run_on_host",
    "my_domain_function",
]
```

This is the standard Python way to declare public API — pylint and other tools respect `__all__`.

---

## 3. Test Writing Rules

### 3.1 Test File Docstring (MANDATORY)

Every test file MUST start with a module docstring listing what it verifies:

```python
"""
<Domain> <Phase> — <Category> Verification.

Validates that --tags <tag> created all required <resources>:
  <resource 1>
  <resource 2>
  <resource 3>
"""
```

### 3.2 FVT/NFT Test Case ID Registry (`TEST_CASES` dict) — MANDATORY

All FVT/NFT test-case metadata (TC ID, title) MUST be defined in
`library/vars/test_case_vars.py` and referenced via `TEST_CASES["key"]` in test
files. **Never hardcode TC IDs or titles.** UT mappings follow section 3.10.

```python
# In library/vars/test_case_vars.py:
TEST_CASES = {
    "deploy_prepare": {
        "id": "IMGBM_FVT_PREPARE_E001",
        "title": "Deploy <domain_name> (prepare)",
    },
    "verify_resource": {
        "id": "IMGBM_FVT_PREPARE_V001",
        "title": "Verify <resource> after prepare",
    },
}
```

**Rules:**

| Rule | Allowed | Forbidden |
|------|---------|-----------|
| TC ID source | `TC["key"]["id"]` | Hardcoded `"IMGBM_FVT_PREPARE_V001"` in test code |
| Title source | `TC["key"]["title"]` | Hardcoded string in test code |
| TestLogger init | `TestLogger(tc["title"], tc["id"])` | `TestLogger("...", "IMGBM_FVT_PREPARE_V001")` |
| Docstring | Description only (no TC IDs) | `"""IMGBM_FVT_PREPARE_V001: Verify ...` |
| Dict keys | Match function name without `test_` prefix | Arbitrary keys |

**Verification** — this grep must return zero results:
```bash
grep -Ern "['\"]IMGBM_(FVT|NFT|UT)_[A-Z0-9_]+['\"]" fvt/ nft/ ut/ \
  --include="*.py"
```

### 3.3 Test Function Structure (MANDATORY)

```python
@pytest.mark.sanity
@pytest.mark.order(1)
def test_verify_resource(host):
    """Verify resource exists after deploy."""
    tc = TC["verify_resource"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_resource(host)

    if result.get("skipped"):
        tl.skipped(LOG["resource_skip_reason"])
        pytest.skip(LOG["resource_skip_reason"])

    if result["success"]:
        tl.passed(LOG["resource_ok"], result["details"])
    else:
        tl.failed(LOG["resource_not_found"].format(name="..."))

    assert result["success"], ASSERT["resource_not_found"].format(
        name="...", status=result.get("status", ""),
    )
```

**Key rules:**
- TC ID and title from `TEST_CASES` dict — never hardcode
- `TestLogger` for structured output — never use `print()`
- Verification function returns a dict — test file does not contain logic
- Log and assert messages from centralized message dicts

### 3.4 Test Case ID Convention

| Format | Rule |
|--------|------|
| **Pattern** | `<DOMAIN>_FVT_<PHASE>_<TYPE><SEQ>` |
| **Domain** | Stable uppercase domain code, such as `IMGBM` for Image Build Manager |
| **Level** | `FVT` identifies a Functional Verification Test |
| **Phase** | Runner lifecycle phase, such as `PRECHECK`, `VALIDATE`, `PREPARE`, `BUILD`, or `CLEANUP` |
| **Type** | `E` when the test runs a playbook; `V` when it verifies postconditions |
| **Sequence** | Three digits appended to the type, starting at `001` |

Examples:

| ID | Meaning |
|----|---------|
| `IMGBM_FVT_PREPARE_E001` | Run the Image Build Manager prepare playbook |
| `IMGBM_FVT_PREPARE_V001` | Verify the first prepare postcondition |
| `IMGBM_FVT_BUILD_V006` | Verify a stable Image Build Manager build contract |

IDs remain stable when execution order changes, and retired IDs must not be
reused. Existing modules with legacy IDs may retain them until an atomic
migration updates the registry, documentation, runtime output, and a complete
legacy-to-current mapping together.

### 3.5 Deploy Test Pattern

Deploy tests run the playbook and always execute first (`order(0)`):

```python
@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_prepare(host):
    """Deploy <domain_name> --tags prepare."""
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

    assert result["success"], ASSERT["playbook_failed"].format(
        playbook=PLAYBOOK_ENTRY_POINT, tag="prepare",
        rc=result["rc"], duration=result["duration"],
        log_path=BUILD_LOG_PATH.format(shared_path=SHARED_PATH, project=project),
    )
```

**run_playbook Rules:**
- **Always pass `playbook=` explicitly** — use `PLAYBOOK_ENTRY_POINT` constant from `common_vars.py`
- **TC ID and title** come from `TEST_CASES` dict — never hardcode
- **Timeout** should be appropriate for the tag (3600s for full, 1800s for single tag)

### 3.6a Precheck Test Pattern

Precheck tests validate the environment before any playbook runs. They verify
env vars from `omnia.env`, hostname, domain, admin IP, and `omnia.sh` setup:

```python
@pytest.mark.sanity
@pytest.mark.order(2)
def test_env_vars_present(host):
    """Verify all required omnia.env variables present on target."""
    tc = TC["env_vars_present"]
    tl = TestLogger(tc["title"], tc["id"])
    result = check_env_vars_present(host)

    if result["success"]:
        tl.passed(LOG["env_vars_ok"], result["details"])
    else:
        missing = [r for r in result["results"] if not r["found"]]
        tl.failed(LOG["env_vars_missing"].format(count=len(missing)), result["details"])

    assert result["success"], ASSERT["env_vars_missing"].format(
        error=result.get("error", "Env vars missing"),
    )
```

**Precheck tests verify:**
- SSH connectivity (`check_target_connectivity`)
- All omnia.env vars: `OMNIA_DATA_PATH`, `OMNIA_PROJECT_NAME`,
  `SYSTEM_ADMIN_NIC_IPV4`, `SYSTEM_HOSTNAME`, `SYSTEM_DOMAIN_NAME`
- Hostname matches configured `SYSTEM_HOSTNAME`
- Admin IP assigned to a local interface
- `omnia.sh --setup-venv` completed (`/etc/omnia/omnia.env` exists)

**Source playbook**: Each domain should have a `precheck/` playbook directory
with a `precheck_environment` role that validates the same checks via Ansible.

### 3.6 Import Structure for Test Files

```python
# Third-party
import pytest

# Local — Functions (ONLY from library, NEVER from omnia_auto directly)
from library.functions import (
    TestLogger,
    run_playbook,
    check_resource,
)

# Local — Variables (TEST_CASES, constants)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import (
    PLAYBOOK_ENTRY_POINT,
    RESOURCE_CONSTANT,
)

# Local — Messages
from library.messages import (
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)
```

**Import Rules:**
- **Never import from `omnia_auto` directly in test files** — use `library.functions`
- **TEST_CASES** comes from `library.vars`
- **PLAYBOOK_ENTRY_POINT** must be imported for deploy tests
- **Messages** aliased as `LOG` and `ASSERT` for readability

### 3.7 Test Output Format

Tests produce structured output via `TestLogger`:

```
  ▶ Verify resource is running
  ✔ PASS: Resource is active
    │ Status: Up 3 hours
```

**Never use `print()` directly.** Always use `TestLogger` or `log()`.

### 3.10 Unit Test Case IDs

Unit-test IDs use `<DOMAIN>_UT_<SEQ>` (for example, `IMGBM_UT_001`). Keep the
mapping between each test file/class/method node and its test-case ID in one
central registry; do not embed numeric IDs independently in test methods.
Parameterized variants may share the method-level ID. Store IDs explicitly so
source reordering cannot renumber published cases, and append new mappings
with the next available ID.

### 3.11 Non-Functional Tests (NFT)

NFT tests live in `nft/` alongside `fvt/` and validate **performance** and **idempotency**.

**NFT Rules:**

1. **Directory**: Place NFT tests in `test/<domain>/nft/`, not in `fvt/`.
2. **Marker**: All NFT tests MUST use `@pytest.mark.nft`.
3. **README**: Each `nft/` directory MUST contain a `README.md` documenting test cases, thresholds, and execution instructions.
4. **TC ID Prefix**: NFT test-case IDs use `<DOMAIN>_NFT_` (for example,
   `IMGBM_NFT_001`).
5. **Thresholds**: Performance thresholds MUST be defined as module-level constants, not inline.
6. **Prerequisites**: NFT tests require a fully deployed environment. Document prerequisites in the `README.md`.
7. **Execution**: NFT tests are run via `./run_validation.sh nft test`.

```python
import pytest

PREPARE_THRESHOLD = 300  # 5 minutes

@pytest.mark.nft
@pytest.mark.order(1)
def test_prepare_performance(run_playbook):
    """IMGBM_NFT_001: Prepare completes within threshold."""
    start = time.time()
    result = run_playbook(tag="prepare", timeout=PREPARE_THRESHOLD + 60)
    elapsed = time.time() - start
    assert result.rc == 0, f"Prepare failed: rc={result.rc}"
    assert elapsed <= PREPARE_THRESHOLD, f"Exceeded {PREPARE_THRESHOLD}s: {elapsed:.1f}s"
```

---

## 4. Verification Function Rules

### 4.1 Return Dictionary Pattern (MANDATORY)

All verification functions MUST return a dict:

```python
def check_resource(host, name: str) -> Dict[str, Any]:
    """Check if a resource exists on the target host.

    Args:
        host: Testinfra host connection.
        name: Name of the resource to check.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    cmd = CMDS["check_resource"].format(name=name)
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {"success": False, "details": "", "error": f"{name} not found"}
    return {"success": True, "details": f"{name} is present", "error": ""}
```

### 4.2 Dynamic Input Rules (CRITICAL)

**NEVER hardcode:**
- IP addresses or hostnames
- File paths that vary by environment
- Credentials or secrets
- Port numbers (use constants from `common_vars.py`)

**ALWAYS:**
- Read from `test_config.yml` via `load_test_config()`
- Use `CMDS` dict for shell commands
- Use constants from `common_vars.py` for paths and ports

### 4.3 Skip Pattern for Optional Features

```python
if not items:
    return {
        "success": True,
        "skipped": True,
        "details": f"No {category} configured — skipping",
    }
```

### 4.4 Docstrings (MANDATORY)

Every function must have a docstring explaining:

- **What** it does (one-line summary)
- **Parameters** (if not obvious from type hints)
- **Returns** (structure of the return dict/value)

---

## 5. Variables Module Rules

### 5.1 No Hardcoded Values — Centralize Everything

**Every constant, path, and shell command MUST live in `library/vars/common_vars.py`.**
Violating these rules will block code review.

#### 5.1.1 No Hardcoded Paths in Function or Test Files

| Violation | Correct |
|-----------|---------|
| `"/tmp/test_image"` inline | `TEMP_IMAGE_PATH` in `common_vars.py` |
| `"/opt/omnia/<domain>/output"` inline | `OUTPUT_PATH` in `common_vars.py` |
| `"config_file.yml"` inline | `CONFIG_FILE_NAME` in `common_vars.py` |

**Rule:** If a string literal represents a filesystem path, package name, container
name, port number, bucket name, or service name — it MUST be a named constant in
`common_vars.py`, exported from `vars/__init__.py`, and imported where needed.

#### 5.1.2 No Inline Shell Commands in Function or Test Files

All shell commands executed via `host.run()` MUST use the `CMDS` dictionary in
`common_vars.py`.

| Violation | Correct |
|-----------|---------|
| `host.run(f"cat {path} 2>/dev/null")` | `host.run(CMDS["cat_file"].format(path=path))` |
| `host.run(f"podman ps --format ... --filter ...")` | `host.run(CMDS["podman_ps_check"].format(container=name))` |
| `host.run(f"systemctl is-active {svc}")` | `host.run(CMDS["systemctl_is_active"].format(service=svc))` |

**Rule:** Never write a raw shell command string inside `host.run()`. Always
add the command template to `CMDS` with descriptive named placeholders, then
call `CMDS["key"].format(...)` at the call site.

#### 5.1.3 No Hardcoded Validation Constants

Regex patterns, required field lists, and required file lists used in
`validation_func.py` MUST be defined in `common_vars.py`:

```python
# In common_vars.py:
IPV4_PATTERN = re.compile(r'...')
REQUIRED_CONFIG_FIELDS = ["project_name", "clone_path", ...]
REQUIRED_DATASET_FILES = ["input/<domain_name>_config.yml", ...]
```

### 5.2 Command Dictionary (MANDATORY)

All shell commands MUST be in the `CMDS` dict in `common_vars.py`:

```python
CMDS: Dict[str, str] = {
    "podman_ps_check": (
        "podman ps --format '{{.Names}}'"
        " --filter name=^{container}$ 2>/dev/null"
    ),
    "systemctl_is_active": "systemctl is-active {service} 2>/dev/null",
    "file_exists": "test -f {path} && echo exists",
    "cat_file": "cat {path} 2>/dev/null",
}
```

### 5.3 CMDS Naming Convention

| Category | Prefix | Example |
|----------|--------|---------|
| Podman | `podman_` | `podman_ps_check`, `podman_inspect` |
| S3/s3cmd | `s3cmd_` | `s3cmd_ls`, `s3cmd_ls_bucket` |
| Registry | `curl_registry_` | `curl_registry_catalog`, `curl_registry_tags` |
| File operations | descriptive | `cat_file`, `file_exists`, `dir_exists`, `file_stat` |
| System | descriptive | `hostname_cmd`, `rpm_check`, `which_cmd` |
| Systemd | `systemctl_` | `systemctl_is_active` |

### 5.4 Adding a New Command or Constant — Checklist

When you need a new shell command or constant:

1. **Add the constant** to `common_vars.py` with a descriptive comment.
2. **Add the export** to `vars/__init__.py`.
3. **Import it** in the function file that uses it.
4. **Use `.format()` with named placeholders** — never positional `%s` or f-string interpolation inside CMDS values.
5. **Verify** with `python -c "from library.vars import CMDS; print(CMDS['new_key'])"`.

### 5.5 Domain Constants

```python
# Domain identity
DOMAIN_NAME = "<domain_name>"

# Playbook config
PLAYBOOK_ENTRY_POINT = "<domain_name>.yml"
PLAYBOOK_WORKDIR = "src/<domain_name>/playbooks"

# Domain-specific resources (examples)
CONTAINER_NAMES = ["container_a", "container_b"]
SYSTEMD_SERVICES = ["service_a.service", "service_b.service"]
FIREWALL_PORTS = ["8080/tcp", "443/tcp"]
```

### 5.6 TEST_CASES Dictionary (MANDATORY)

All FVT/NFT test-case metadata MUST be centralized in `test_case_vars.py`:

```python
TEST_CASES: Dict[str, Dict[str, str]] = {
    "deploy_prepare": {
        "id": "IMGBM_FVT_PREPARE_E001",
        "title": "Deploy <domain_name> (prepare)",
    },
    "verify_resource": {
        "id": "IMGBM_FVT_PREPARE_V001",
        "title": "Verify <resource> after prepare",
    },
}
```

**Rules:**
- Keys match test function names (without `test_` prefix)
- Each entry has `id` and `title` only
- Tests look up TC ID and title from this dict — never hardcode
- Order and markers are defined via pytest decorators, not in TEST_CASES

### 5.7 Pre-Commit Violation Check

Before committing, run this check to detect inline command violations:

```bash
python3 -c "
with open('library/functions/<domain_name>_func.py') as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    s = line.strip()
    if 'host.run(' in s and 'CMDS[' not in s:
        ctx = ''.join(lines[max(0,i-2):min(len(lines),i+2)])
        if 'CMDS[' not in ctx:
            print(f'VIOLATION L{i}: {s}')
"
```

This must print **no output**. Any violation means an inline command exists
that has not been moved to `CMDS`.

---

## 6. Messages Module Rules (MANDATORY)

### 6.1 Required Dictionaries

Every domain module defines message dictionaries in `<domain_name>_msgs.py`:

```python
# --- Log Messages ---
TEST_LOG_MSGS: Dict[str, str] = {
    "playbook_success": "Playbook completed in {duration}",
    "resource_ok": "Resource '{name}' is present",
    "resource_not_found": "Resource '{name}' not found",
}

# --- Assertion Messages ---
TEST_ASSERT_MSGS: Dict[str, str] = {
    "playbook_failed": (
        "Playbook {playbook} --tags {tag} failed (rc={rc})\n"
        "HOW TO FIX:\n"
        "  1. Check logs at: {log_path}\n"
        "  2. Run manually on the target server\n"
    ),
    "resource_not_found": (
        "Expected '{name}' to be present, got '{status}'\n"
        "HOW TO FIX:\n"
        "  1. Run --tags <tag> first\n"
        "  2. Check: <diagnostic command>\n"
    ),
}
```

### 6.2 Rules

- **ALL log messages** go in `TEST_LOG_MSGS` — never inline in function files.
- **ALL assertion messages** go in `TEST_ASSERT_MSGS` — never inline in test files.
- Use `.format()` with named placeholders for dynamic content.
- Keys use `snake_case` matching the test or function name.
- Assertion messages SHOULD include a "HOW TO FIX" section with actionable steps.

---

## 7. Code Quality Standards

### 7.1 Pylint Score

- **Minimum score: 8.8/10** per file (team standard), **8.0** in CI.
- Run pylint from the module's virtual environment (where `omnia-auto` is installed):
  ```bash
  .venv/bin/pylint library/functions/<domain_name>_func.py
  ```
- **Do NOT use `# noqa` or `# pylint: disable=...` to suppress warnings.**
  Fix the actual issue instead:
  - `unused-import` on re-exports: use `__all__` to declare public API
  - `import-error`: add the package to `requirements.txt`
  - `unused-argument`: use `_` prefix (e.g., `_host`) for intentionally unused params
  - `wrong-import-position`: move all imports to the top of the file
  - `too-many-branches`: refactor into smaller helper functions

### 7.2 Test Naming Convention

| Type | Convention | Example |
|------|-----------|---------|
| Test function | `test_<feature>_<aspect>` | `test_resource_after_prepare` |
| Test file | `test_<component>.py` | `test_containers.py` |
| FVT case ID | `<DOMAIN>_FVT_<PHASE>_<TYPE><SEQ>` | `IMGBM_FVT_PREPARE_V001` |
| NFT case ID | `<DOMAIN>_NFT_<SEQ>` | `IMGBM_NFT_001` |
| UT case ID | `<DOMAIN>_UT_<SEQ>` | `IMGBM_UT_001` |

---

## 8. CI Checks (All Must Pass)

The following CI workflows run on every PR. **All must pass before merge.**

| Check | Tool | Rule |
|-------|------|------|
| **DCO** | `dco` | Every commit signed off (`git commit -s`) |
| **Flake8** | `flake8` | No errors with `--max-line-length=100` |
| **Pylint** | `pylint` | Score >= 8.0 per file |
| **Bandit** | `bandit` | No High severity issues (`-ll -ii`) |
| **Gitleaks** | `gitleaks` | No secrets in committed code |
| **Ansible Lint** | `ansible-lint` | YAML best practices (`true`/`false` not `yes`/`no`, newline at EOF) |
| **pip-audit** | `pip-audit` | No vulnerable Python dependencies |
| **Checkmarx** | SAST | No hardcoded credentials, no insecure file operations |

### 8.1 How to Run Each Check Locally

Run these commands from the module root (e.g., `test/telemetry/`) before every commit.

#### DCO — Developer Certificate of Origin

Every commit MUST include `Signed-off-by:`. Use the `--signoff` flag:

```bash
git commit --signoff -m "feat(telemetry): description"
```

Verify existing commits:
```bash
git log --format='%H %s' origin/main..HEAD | while read hash msg; do
  git log --format='%(trailers:key=Signed-off-by)' -1 "$hash" | grep -q 'Signed-off-by' \
    || echo "MISSING DCO: $hash $msg"
done
```

#### Flake8 — Style and Error Linting

```bash
source .venv/bin/activate

# Lint all module code (exclude venv)
flake8 library/ fvt/ conftest.py --max-line-length=100 --exclude=.venv --count

# Lint a single file
flake8 library/functions/telemetry_func.py --max-line-length=100
```

**Result must be 0 errors.** The only permitted `# noqa` is `E402` in
`conftest.py` where imports MUST follow `sys.path.insert()` and
`omnia_auto.configure()`. All other suppressions are prohibited — fix the
underlying issue instead.

#### Pylint — Code Quality Score

```bash
source .venv/bin/activate
pylint library/functions/*.py library/vars/*.py library/messages/*.py
```

**Minimum score: 8.8/10 locally, 8.0 in CI.**

#### Bandit — Security Scanner

```bash
source .venv/bin/activate

# Scan all library and test code
bandit -r library/ fvt/ -ll -ii

# Scan with detailed output
bandit -r library/ fvt/ -ll -ii -f json -o bandit_report.json
```

**Result must have zero High/Medium severity findings.** Common false positives:
- `B603` (subprocess call): acceptable when using `run_on_host()` from `omnia_auto`
- `B108` (/tmp usage): use constants from `common_vars.py` instead of inline `/tmp`

#### Gitleaks — Secret Detection

```bash
# Scan staged changes
grep -rn -iE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' \
    --include="*.py" --include="*.yml" | \
    grep -v '127\.0\.0\.1' | grep -v '0\.0\.0\.0'

# Scan for hardcoded passwords/tokens
grep -rn -iE '(password|secret|token|api.?key)\s*=\s*["'"'"'][^"'"'"']+["'"'"']' \
    --include="*.py" --include="*.yml" | \
    grep -v 'CHANGE_ME' | grep -v 'placeholder' | grep -v '""'
```

**Both must return empty results.**

#### pip-audit — Dependency Vulnerabilities

```bash
source .venv/bin/activate
pip-audit
```

**Zero known-vulnerable packages allowed.**

---

## 9. Security Rules

### 9.1 No Hardcoded Secrets

- **Never commit real IPs, passwords, hostnames, or tokens.**
- `test_config.yml` must ship with `oim_server_ip: ""` — user fills in locally.
- `test_creds.yml` must ship with `oim_password: ""` — user fills in locally.
- Credentials file is auto-encrypted with Ansible Vault on first run.

### 9.2 Pre-Push Security Scan

Before every push, run:

```bash
# Check for hardcoded IPs
grep -rn -iE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' \
    --include="*.py" --include="*.yml" | \
    grep -v '127\.0\.0\.1' | grep -v '0\.0\.0\.0'

# Check for hardcoded passwords/secrets
grep -rn -iE '(password|secret|token|api.?key)\s*=\s*["'"'"'][^"'"'"']+["'"'"']' \
    --include="*.py" --include="*.yml" | \
    grep -v 'CHANGE_ME' | grep -v 'placeholder'
```

Both must return empty results.

---

## 10. Environment Setup and Testing

### 10.1 Setup (One-Time)

```bash
cd test/<domain_name>/

# Step 1: Run setup script to create venv and install dependencies
./setup_env.sh --venv

# Step 2: Activate the virtual environment
source .venv/bin/activate

# Step 3: Generate a dataset
cd datasets/generator/
python generate_dataset.py my_dataset defaults
cd ../..

# Step 4: Configure test settings
vi test_config.yml        # Set oim_server_ip, dataset, paths, options

# Step 5: Set SSH credentials (password-based remote mode only)
./setup_env.sh --set-creds

# Step 5b: Set domain credentials (no oim_server_ip needed)
./setup_env.sh --set-domain-creds
```

`setup_env.sh` installs all dependencies from `requirements.txt` (including `omnia-auto`
from `../plugins/dist/omnia_auto-1.0.0-py3-none-any.whl`).

### 10.2 Running Tests — Use `run_validation`, NOT `pytest`

**Always use `run_validation.sh` to run tests.** Never invoke `pytest` directly.

```bash
# Verify a specific scenario
./run_validation.sh <scenario> verify --marker sanity

# Deploy + verify
./run_validation.sh <scenario> test

# Run a specific suite within a scenario
./run_validation.sh <scenario> verify --suite <suite_name>

# Full batch from config
./run_validation.sh --config

# List available scenarios
./run_validation.sh list
```

### 10.3 Test Iteration Loop

```
Write code -> Run tests -> Fix failures -> Re-run tests -> All pass -> Push
                 ^                              |
                 +------------------------------+
```

**Never push with known failures. Never skip a failing test to "fix later".**

---

## 11. Feature Testing Workflow

### 11.1 Writing Tests for a New Feature

```
1. Read the playbook source code (src/<domain_name>/)
2. Identify what resources the playbook creates
3. Manually verify on a working cluster
4. Check omnia_auto for existing verification functions
5. Write domain-specific verification function in <domain_name>_func.py
6. Add constants to common_vars.py, commands to CMDS dict
7. Add TC entry to test_case_vars.py
8. Write the test in fvt/<scenario>/<suite>/
9. Add messages to <domain_name>_msgs.py
10. Add TC ID to fvt/README.md
11. Run pylint + bandit + tests
12. Push
```

### 11.2 Rebuilding the `omnia-auto` Wheel

If you modify the shared plugin code in `test/plugins/omnia_auto/`:

```bash
cd test/plugins/

# 1. Run pylint on the plugin
pylint omnia_auto/

# 2. Run bandit
bandit -r omnia_auto/ -ll -ii

# 3. Rebuild the wheel
rm -rf dist/ build/ *.egg-info
python -m build --wheel

# 4. Reinstall in the domain venv
cd ../<domain_name>/
source .venv/bin/activate
pip install --force-reinstall ../plugins/dist/omnia_auto-1.0.0-py3-none-any.whl

# 5. Verify the install
python -c "import omnia_auto; print(omnia_auto.__version__)"
```

---

## 12. Git Commit Rules (MANDATORY)

### 12.1 Commit Format

```bash
git commit --signoff \
  --author="Your Name <your.email@dell.com>" \
  -m "<type>(<scope>): <description>"
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### 12.2 Commit Message Rules

- **First line**: `<type>(<scope>): <description>` (max 72 chars)
- **Body** (optional): Blank line, then details in bullet points
- **Signed-off-by**: Auto-added by `--signoff` flag
- **No Co-Authored-By tags** — do NOT include `Co-Authored-By: Devin <...>` or any AI agent attribution in commits. Only the human developer's `Signed-off-by` should appear.

### 12.3 Branch Naming

```
feature/<issue>-<short-description>
bugfix/<issue>-<short-description>
```

---

## 13. Full Pre-Push Verification Checklist

Run this sequence before every push:

```bash
source .venv/bin/activate

# 1. Flake8 — zero errors
flake8 library/ fvt/ conftest.py --max-line-length=100 --exclude=.venv --count

# 2. Pylint — all changed files must score >= 8.8
pylint library/functions/*.py library/vars/*.py library/messages/*.py

# 3. Bandit — no High severity
bandit -r library/ fvt/ -ll -ii

# 4. Gitleaks — no secrets
grep -rn -iE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' \
    --include="*.py" --include="*.yml" | \
    grep -v '127\.0\.0\.1' | grep -v '0\.0\.0\.0'

# 5. Run tests — all must pass
./run_validation.sh <scenario> verify --marker sanity

# 6. Commit with DCO sign-off and push
git commit --signoff -m "<type>(<scope>): description"
git push
```

---

## 14. Quality Checklist

Before submitting a PR, verify:

### Module Structure
- [ ] Follows `functions/`, `vars/`, `messages/` structure
- [ ] All `__init__.py` files properly export items with `__all__`
- [ ] `conftest.py` calls `omnia_auto.configure()` before any other `omnia_auto` imports
- [ ] `library/functions/__init__.py` re-exports `omnia_auto` functions + domain wrappers
- [ ] License headers in all files (current year)

### Dataset
- [ ] Dataset created using `datasets/generator/generate_dataset.py`
- [ ] Generator has `defaults.yml` profile and Jinja2 templates
- [ ] Generated dataset contains all required input files

### Functions
- [ ] Used `omnia_auto` core functions first (check before writing new)
- [ ] Return dicts with `success`, `details`, `error` keys
- [ ] Docstrings on every function
- [ ] No inline shell commands — all in `CMDS`
- [ ] No hardcoded paths — all in `common_vars.py`

### Tests
- [ ] TC IDs and titles from `TEST_CASES` dict — never hardcoded
- [ ] Imports only from `library.*`, never from `omnia_auto` directly
- [ ] All messages from `TEST_LOG_MSGS` / `TEST_ASSERT_MSGS`
- [ ] `@pytest.mark.order(n)` on every test (deploy = 0, verify >= 1)
- [ ] `TestLogger` used in every test — no `print()`

### Variables
- [ ] All constants in `common_vars.py`
- [ ] All commands in `CMDS` dict with named placeholders
- [ ] All test case metadata in `test_case_vars.py`

### Messages
- [ ] Log messages in `TEST_LOG_MSGS`
- [ ] Assert messages in `TEST_ASSERT_MSGS` with HOW TO FIX sections
- [ ] `.format()` with named placeholders for dynamic content

### CI
- [ ] Flake8: zero errors (`--max-line-length=100`)
- [ ] Pylint >= 8.8 locally, >= 8.0 in CI
- [ ] Bandit: zero high-severity findings
- [ ] No hardcoded IPs, passwords, tokens
- [ ] All commits signed off (`git commit --signoff`)
- [ ] No `Co-Authored-By` tags in commits (no AI agent attribution)
- [ ] fvt/README.md updated with new test cases

### Co-Change
- [ ] PR that changes `src/` includes corresponding `test/` updates (or justification in PR description)
- [ ] New playbook tags have a corresponding FVT scenario
- [ ] Deleted features have their tests removed
- [ ] AI agents (Devin, Copilot, etc.) NOT used for sign-off — see `general.md` §7
- [ ] No `Co-Authored-By` or `Generated with` tags in commit messages
