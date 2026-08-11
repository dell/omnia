# Test Automation — Coding Rules

> All test automation code under `test/` MUST follow these rules.
> These rules apply to every domain test module (image_build_manager, repo_manager, provision, discovery, telemetry, etc.).
> The reference implementation is `test/image_build_manager/`.

---

## 1. Pre-Development Analysis (MANDATORY)

### 1.1 Analyze the Source Code First

Before writing **any** automation code:

1. **Read the playbook source** under `src/<domain_name>/playbooks/` and `src/<domain_name>/roles/`.
2. **Identify all roles** the playbook calls, what hosts it targets, and what resources it creates (containers, services, files, pods, configs).
3. **Map each resource to a verification test** — every container the playbook creates should have a test that checks it is running, every service should be checked as active, etc.

```bash
# Example: analyze image_build_manager
ls src/image_build_manager/playbooks/       # Main playbook entry points
ls src/image_build_manager/roles/           # All 10 roles
cat src/image_build_manager/playbooks/prepare/prepare_image_build_manager.yml
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
├── test_creds.yml                 # Sensitive credentials (auto-encrypted)
├── requirements.txt               # Dependencies including omnia-auto wheel
├── run_validation.sh              # CLI runner
├── setup_env.sh                   # One-time venv + tab-completion setup
├── datasets/
│   └── data_set_01/
│       └── input/                 # Synced to target
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
└── fvt/
    ├── TEST_CASES.md              # All test cases documented
    ├── <scenario>/                # One dir per playbook tag
    │   ├── test_playbook.py       # Deploy test
    │   └── <suite>/test_<suite>.py
    └── <domain_name>/             # Full end-to-end (no tag)
```

### 2.2 Strict Separation Rules

| Content | Location | Never In |
|---------|----------|----------|
| Shell commands | `CMDS` dict in `common_vars.py` | Test files, function files |
| TC IDs and titles | `TEST_CASES` dict in `test_case_vars.py` | Test files (hardcoded) |
| Log messages | `TEST_LOG_MSGS` in `<domain_name>_msgs.py` | Test files |
| Assert messages | `TEST_ASSERT_MSGS` in `<domain_name>_msgs.py` | Test files |
| Constants | `common_vars.py` | Function or test files |
| Verification logic | `functions/<domain_name>_func.py` | Test files |

### 2.3 `__init__.py` Requirements

Every `__init__.py` MUST:
1. Include Apache 2.0 license header (current year)
2. Provide a module docstring
3. Import and re-export specific items (no `import *`)
4. Group imports: functions, then vars, then messages

### 2.4 Re-exports with `__all__`

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
Image Build Prepare — Infrastructure Verification.

Validates that --tags prepare created all required infrastructure:
  S3 storage backend (MinIO container)
  Registry container running
  Systemd services active (minio, registry)
  Firewall ports open (9000, 9001, 5000)
  s3cmd installed and configured
  Registry reachable (HTTP catalog)
"""
```

### 3.2 Test Case ID Registry (`TEST_CASES` dict) — MANDATORY

All test case metadata (TC ID, title) MUST be defined in `library/vars/test_case_vars.py`
and referenced via `TEST_CASES["key"]` in test files. **Never hardcode TC IDs or titles.**

```python
# In library/vars/test_case_vars.py:
TEST_CASES = {
    "deploy_prepare": {
        "id": "TC_PR_001",
        "title": "Deploy image_build_manager (prepare)",
    },
    "storage_backend": {
        "id": "TC_PR_002",
        "title": "Verify S3 storage backend after prepare",
    },
}
```

**Rules:**

| Rule | Allowed | Forbidden |
|------|---------|-----------|
| TC ID source | `TC["key"]["id"]` | Hardcoded `"TC_PR_002"` in test code |
| Title source | `TC["key"]["title"]` | Hardcoded string in test code |
| TestLogger init | `TestLogger(tc["title"], tc["id"])` | `TestLogger("...", "TC_PR_002")` |
| Docstring | Description only (no TC IDs) | `"""TC_PR_002: Verify ...` |
| Dict keys | Match function name without `test_` prefix | Arbitrary keys |

**Verification** — this grep must return zero results:
```bash
grep -rn '"TC_[A-Z]*_[0-9]' fvt/ --include="*.py" | grep -v __pycache__ | grep -v test_case_vars
```

### 3.3 Test Function Structure (MANDATORY)

```python
@pytest.mark.sanity
@pytest.mark.order(1)
def test_storage_backend_after_prepare(host):
    """Verify S3 backend after prepare."""
    tc = TC["storage_backend"]
    tl = TestLogger(tc["title"], tc["id"])

    result = check_s3_containers(host)

    if result.get("skipped"):
        tl.skipped(LOG["storage_backend_skip_minio_check"])
        pytest.skip(LOG["storage_backend_skip_minio_check"])

    if result["success"]:
        tl.passed(LOG["storage_backend_minio"], result["details"])
    else:
        tl.failed(LOG["container_not_running"].format(container="minio-server"))

    assert result["success"], ASSERT["container_not_running"].format(
        container="minio-server", status=result.get("status", ""),
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
| **Pattern** | `TC_<AREA>_<SEQ>` (3-digit zero-padded) |
| **Area** | 2-letter abbreviation of the test phase or scenario |
| **Sequence** | Sequential within that area, starting at `001` (or `001` for deploy) |

Each domain defines its own area prefixes. Common examples:

| Area | Prefix | Description |
|------|--------|-------------|
| Validate | `TC_VL_` | Input validation tests |
| Prepare | `TC_PR_` | Infrastructure setup tests |
| Build | `TC_BD_` | Build/execute phase tests |
| Cleanup | `TC_CL_` | Cleanup verification tests |
| End-to-End | `TC_IB_` | Full suite verification (image_build_manager) |

### 3.5 Deploy Test Pattern

Deploy tests run the playbook and always execute first (`order(0)`):

```python
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

    assert result["success"], ASSERT["playbook_failed"].format(
        playbook="image_build_manager.yml", tag="prepare",
        rc=result["rc"], duration=result["duration"],
        log_path=BUILD_LOG_PATH.format(shared_path=SHARED_PATH, project=project),
    )
```

**run_playbook Rules:**
- **Always pass `playbook=` explicitly** — use `PLAYBOOK_ENTRY_POINT` constant from `common_vars.py`
- **TC ID and title** come from `TEST_CASES` dict — never hardcode
- **Timeout** should be appropriate for the tag (3600s for full, 1800s for single tag)

### 3.6 Import Structure for Test Files

```python
# Third-party
import pytest

# Local — Functions (ONLY from library, NEVER from omnia_auto directly)
from library.functions import (
    TestLogger,
    run_playbook,
    check_s3_containers,
)

# Local — Variables (TEST_CASES, constants)
from library.vars import TEST_CASES as TC
from library.vars.common_vars import (
    PLAYBOOK_ENTRY_POINT,
    REGISTRY_CONTAINER,
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
  ▶ Verify container is running
  ✔ PASS: Container registry is running
    │ Status: Up 3 hours
```

**Never use `print()` directly.** Always use `TestLogger` or `log()`.

---

## 4. Verification Function Rules

### 4.1 Return Dictionary Pattern (MANDATORY)

All verification functions MUST return a dict:

```python
def check_container_running(host, container_name: str) -> Dict[str, Any]:
    """Check if a container is running on the target host.

    Args:
        host: Testinfra host connection.
        container_name: Name of the container to check.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
    cmd = CMDS["podman_ps_check"].format(container=container_name)
    result = run_on_host(host, cmd)
    if result.rc != 0:
        return {"success": False, "details": "", "error": f"{container_name} not found"}
    return {"success": True, "details": f"{container_name} is present", "error": ""}
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
if not groups:
    return {
        "success": True,
        "skipped": True,
        "details": f"No {arch} functional groups configured",
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
| `"/tmp/ibm_test_image"` inline | `IMAGE_VERIFY_TEMP_IMAGE` in `common_vars.py` |
| `"/opt/omnia/repo_manager/output"` inline | `REPO_MANAGER_OUTPUT_PATH` in `common_vars.py` |
| `"functional_group_packages.yml"` inline | `FG_PACKAGES_FILENAME` in `common_vars.py` |
| `"squashfs-tools"` inline | `SQUASHFS_PACKAGE` in `common_vars.py` |

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
| `host.run(f"mount -t squashfs -o ro {img} {mnt}")` | `host.run(CMDS["mount_squashfs"].format(image=img, mount=mnt))` |
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
REQUIRED_DATASET_FILES = ["input/image_build_config.yml", ...]
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
    "s3cmd_ls": "s3cmd ls 2>/dev/null",
    "curl_registry_catalog": (
        "curl -sk https://{registry}:{port}/v2/_catalog 2>/dev/null"
    ),
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
| Squashfs | `squashfs_` | `squashfs_tools_check`, `squashfs_tools_install` |
| Mount | `mount_`, `umount` | `mount_squashfs`, `umount` |

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
DOMAIN_NAME = "image_build_manager"

# Playbook config
PLAYBOOK_ENTRY_POINT = "image_build_manager.yml"
PLAYBOOK_WORKDIR = "src/image_build_manager/playbooks"

# Domain-specific resources
MINIO_CONTAINER = "minio-server"
REGISTRY_CONTAINER = "registry"
SYSTEMD_SERVICES = ["minio.service", "registry.service"]
FIREWALL_PORTS = ["9000/tcp", "9001/tcp", "5000/tcp"]
```

### 5.6 TEST_CASES Dictionary (MANDATORY)

All test case metadata MUST be centralized in `test_case_vars.py`:

```python
TEST_CASES: Dict[str, Dict[str, str]] = {
    "deploy_prepare": {
        "id": "TC_PR_001",
        "title": "Deploy image_build_manager (prepare)",
    },
    "storage_backend": {
        "id": "TC_PR_002",
        "title": "Verify S3 storage backend after prepare",
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
with open('library/functions/build_image_func.py') as f:
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
    "container_running": "Container '{container}' is running",
    "container_not_running": "Container '{container}' not running",
}

# --- Assertion Messages ---
TEST_ASSERT_MSGS: Dict[str, str] = {
    "playbook_failed": (
        "Playbook {playbook} --tags {tag} failed (rc={rc})\n"
        "HOW TO FIX:\n"
        "  1. Check logs at: {log_path}\n"
        "  2. Run manually: cd <clone>/src/image_build_manager/playbooks && "
        "ansible-playbook image_build_manager.yml --tags {tag}\n"
    ),
    "container_not_running": (
        "Expected container '{container}' to be running, got '{status}'\n"
        "HOW TO FIX:\n"
        "  1. Run --tags prepare first\n"
        "  2. Check: podman ps -a --filter name={container}\n"
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
  .venv/bin/pylint library/functions/build_image_func.py
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
| Test function | `test_<feature>_<aspect>` | `test_storage_backend_after_prepare` |
| Test file | `test_<component>.py` | `test_containers.py` |
| Test case ID | `TC_<AREA>_<SEQ>` | `TC_PR_002` |

---

## 8. CI Checks (All Must Pass)

The following CI workflows run on every PR. **All must pass before merge.**

| Check | Tool | Rule |
|-------|------|------|
| **DCO** | `dco` | Every commit signed off (`git commit -s`) |
| **Pylint** | `pylint` | Score >= 8.0 per file (CI may report `import-error` for `omnia_auto` — expected) |
| **Bandit** | `bandit` | No High severity issues (`-ll -ii`) |
| **Gitleaks** | `gitleaks` | No secrets in committed code |
| **Ansible Lint** | `ansible-lint` | YAML best practices (`true`/`false` not `yes`/`no`, newline at EOF) |
| **pip-audit** | `pip-audit` | No vulnerable Python dependencies |
| **Checkmarx** | SAST | No hardcoded credentials, no insecure file operations |

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
bash setup_env.sh --venv

# Step 2: Activate the virtual environment
source .venv/bin/activate

# Step 3: Configure test settings
vi test_config.yml        # Set oim_server_ip, paths, options

# Step 4: Set SSH password (remote mode only)
bash setup_env.sh --set-password
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
10. Add TC ID to fvt/TEST_CASES.md
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
cd ../image_build_manager/
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

```
feat(image_build_manager): add prepare phase verification tests

- Add TC_PR_001 through TC_PR_008 for prepare tag tests
- Add check_s3_containers, check_services_active functions
- Update TEST_LOG_MSGS and TEST_ASSERT_MSGS

Signed-off-by: Your Name <your.email@dell.com>
```

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

# 1. Pylint — all changed files must score >= 8.8
pylint library/functions/*.py library/vars/*.py library/messages/*.py

# 2. Bandit — no High severity
bandit -r library/ -ll -ii

# 3. Gitleaks — no secrets
grep -rn -iE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' \
    --include="*.py" --include="*.yml" | \
    grep -v '127\.0\.0\.1' | grep -v '0\.0\.0\.0'

# 4. Run tests — all must pass
./run_validation.sh prepare verify --marker sanity
./run_validation.sh validate verify --marker sanity
./run_validation.sh image_build_manager verify --marker sanity

# 5. Only push when everything is green
git commit -s -m "<type>(<scope>): description"
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
- [ ] Pylint >= 8.8 locally, >= 8.0 in CI
- [ ] Bandit: zero high-severity findings
- [ ] No hardcoded IPs, passwords, tokens
- [ ] All commits signed off (`git commit -s`)
- [ ] TEST_CASES.md updated with new test cases
