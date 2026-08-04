# Test Automation — Coding Rules

> All test automation code under `test/` MUST follow these rules.
> These rules apply to every domain test module (image_build_manager, repo_manager, provision, discovery, telemetry, etc.).

---

## 1. Pre-Development Analysis (MANDATORY)

### 1.1 Analyze the Source Code First

Before writing **any** automation code:

1. **Read the playbook source** under `src/<domain_name>/playbooks/` or `src/<domain_name>/roles/`.
2. **Identify all roles** the playbook calls, what hosts it targets, and what resources it creates (containers, services, files, pods, configs).
3. **Map each resource to a verification test** — every container the playbook creates should have a test that checks it is running, every service should be checked as active, etc.

```bash
# Example: analyze a domain's playbook
ls src/<domain_name>/playbooks/       # Main playbook entry points
ls src/<domain_name>/roles/           # All roles
cat src/<domain_name>/playbooks/<tag>.yml  # Read a specific phase
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
│   │   └── common_vars.py         # Constants (container names, paths, CMDS dict)
│   └── messages/
│       └── <domain_name>_msgs.py  # TEST_NAMES, LOG_MSGS, ASSERT_MSGS
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
| Test names | `TEST_NAMES` in `<domain_name>_msgs.py` | Test files |
| Log messages | `LOG_MSGS` in `<domain_name>_msgs.py` | Test files |
| Assert messages | `ASSERT_MSGS` in `<domain_name>_msgs.py` | Test files |
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

Every test file MUST start with a module docstring listing all test cases:

```python
"""
<Domain Name> — <Component> Verification Tests.

TC_<AREA>_001: Verify <aspect 1>
TC_<AREA>_002: Verify <aspect 2>
"""
```

### 3.2 Test Function Structure (MANDATORY)

```python
@pytest.mark.sanity
@pytest.mark.order(1)
def test_verify_resource(host):
    """TC_XX_002: Verify resource is present after deployment."""
    # 1. Initialize logger with centralized test name and TC ID
    tl = TestLogger(TEST_NAMES["verify_resource"], "TC_XX_002")

    # 2. Call verification function (returns dict)
    result = check_something(host)

    # 3. Handle skip (optional features)
    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    # 4. Log pass or fail
    tl.passed(result["details"]) if result["success"] else tl.failed(result["error"])

    # 5. Assert with centralized message
    assert result["success"], ASSERT_MSGS["resource_missing"]
```

### 3.3 Test Case ID Convention

| Format | Rule |
|--------|------|
| **Pattern** | `TC_<AREA>_<SEQ>` (3-digit zero-padded) |
| **Area** | 2-letter abbreviation of the test phase or scenario |
| **Sequence** | Sequential within that area, starting at `001` (or `000` for deploy) |

Each domain defines its own area prefixes. Common examples:

| Area | Prefix | Description |
|------|--------|-------------|
| Validate | `TC_VL_` | Input validation tests |
| Prepare | `TC_PR_` | Infrastructure setup tests |
| Build | `TC_BD_` | Build/execute phase tests |
| Cleanup | `TC_CL_` | Cleanup verification tests |
| End-to-End | `TC_E2E_` | Full suite verification |

### 3.4 Test Naming Convention

| Type | Convention | Example |
|------|-----------|---------|
| Test function | `test_<feature>_<aspect>` | `test_container_running` |
| Test file | `test_<component>.py` | `test_container.py` |
| Test case ID | `TC_<AREA>_<SEQ>` | `TC_PR_003` |

### 3.5 Deploy Test Pattern

Deploy tests run the playbook and always execute first (`order(0)`):

```python
@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_scenario(host):
    """TC_XX_000: Deploy <domain_name> --tags <tag>."""
    tl = TestLogger(TEST_NAMES["deploy_scenario"], "TC_XX_000")
    result = run_playbook(tag="<tag>", timeout=3600)
    tl.passed("Playbook completed") if result["success"] else tl.failed(result["error"])
    assert result["success"], ASSERT_MSGS["deploy_failed"]
```

### 3.6 Import Structure for Test Files

```python
# Third-party
import pytest

# Local — Functions (ONLY from library, NEVER from omnia_auto directly)
from library.functions import TestLogger, check_something

# Local — Messages
from library.messages import TEST_NAMES, ASSERT_MSGS

# Local — Constants (if needed)
from library.vars import SOME_CONSTANT
```

### 3.7 Test Output Format

Tests produce structured output via `TestLogger`:

```
  ▶ Verify container is running
  ✔ PASS: Container my-service is running
    │ Status: Up 3 hours
```

**Never use `print()` directly.** Always use `TestLogger` or `log()`.

---

## 4. Verification Function Rules

### 4.1 Return Dictionary Pattern (MANDATORY)

All verification functions MUST return a dict:

```python
def check_something(host, name: str) -> Dict[str, Any]:
    """Verify something exists on the target.

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
if not groups:
    return {
        "success": True,
        "skipped": True,
        "details": f"No {arch} functional groups configured",
    }
```

---

## 5. Variables Module Rules

### 5.1 Command Dictionary (MANDATORY)

All shell commands MUST be in the `CMDS` dict in `common_vars.py`:

```python
CMDS: Dict[str, str] = {
    "podman_ps_check": (
        "podman ps --format '{{.Names}}'"
        " --filter name=^{container}$ 2>/dev/null"
    ),
    "systemctl_is_active": "systemctl is-active {service} 2>/dev/null",
    "file_exists": "test -f {path} && echo exists",
    # ... domain-specific commands
}
```

### 5.2 Domain Constants

```python
# Domain identity
DOMAIN_NAME = "<domain_name>"

# Playbook config
PLAYBOOK_ENTRY_POINT = "<domain_name>.yml"
PLAYBOOK_WORKDIR = "src/<domain_name>/playbooks"

# Domain-specific resources
CONTAINER_NAMES = ["my-service"]
SYSTEMD_SERVICES = ["my-service.service"]
FIREWALL_PORTS = ["8080/tcp"]
```

### 5.3 Rules

- **No magic numbers** in function or test files — define all numbers as named constants.
- **No inline shell strings** — every command goes in `CMDS`.
- Use `CMDS[key].format(...)` with named placeholders.

---

## 6. Messages Module Rules (MANDATORY)

### 6.1 Required Dictionaries

Every domain module defines three message dictionaries in `<domain_name>_msgs.py`:

```python
TEST_NAMES: Dict[str, str] = {
    "deploy_scenario": "Deploy <domain_name> --tags <tag>",
    "verify_resource": "Verify resource is present",
}

LOG_MSGS: Dict[str, str] = {
    "resource_found": "Resource '{name}' is present: {status}",
    "resource_missing": "Resource '{name}' not found",
}

ASSERT_MSGS: Dict[str, str] = {
    "deploy_failed": "Playbook execution failed for --tags <tag>",
    "resource_missing": (
        "Expected resource '{name}' to be present\n"
        "HOW TO FIX:\n"
        "  1. Check the playbook ran successfully\n"
        "  2. Verify resource manually on the target\n"
    ),
}
```

### 6.2 Rules

- **ALL test names** go in `TEST_NAMES` — never inline in test files.
- **ALL log messages** go in `LOG_MSGS` — never inline in function files.
- **ALL assertion messages** go in `ASSERT_MSGS` — never inline in test files.
- Use `.format()` with named `{placeholder}` syntax for dynamic content.
- Keys use `snake_case` matching the test or function name.
- Include **HOW TO FIX** in assertion messages where helpful.
- Never hardcode IPs in messages — use `<placeholder>` format.

---

## 7. Docstring Rules

### 7.1 Module Docstrings

Every `.py` file must start with a module docstring:

```python
"""
<Domain Name> — <Purpose>

<Brief description of what this module provides.>
"""
```

### 7.2 Function Docstrings (Google Style)

Every function must have a Google-style docstring:

```python
def check_container_running(host, container_name: str) -> Dict[str, Any]:
    """Check if a container is running on the target host.

    Args:
        host: Testinfra host connection.
        container_name: Name of the container to check.

    Returns:
        Dict with keys: success (bool), details (str), error (str).
    """
```

### 7.3 Test Function Docstrings

Test function docstrings MUST start with the TC ID:

```python
def test_container_running(host):
    """TC_PR_002: Verify container is running after prepare."""
```

---

## 8. Code Standards

### 8.1 License Header (MANDATORY)

Every Python file MUST start with:

```python
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
```

For YAML files, use `#` comment style with the same content.

### 8.2 Python Standards

| Rule | Requirement |
|------|-------------|
| **Compatibility** | Python 3.12+ — no deprecated APIs or Python 2 patterns |
| **Pylint score** | ≥ 8.8 per file (team standard), ≥ 8.0 (CI gate) |
| **Line length** | Max 100 characters (break long strings with parentheses) |
| **Indentation** | 4 spaces, no tabs |
| **Type hints** | On all public function parameters and return types |
| **Docstrings** | Google-style on every module, class, and public function |
| **Naming** | `snake_case` for functions/variables, `PascalCase` for classes, `ALL_CAPS` for constants |
| **Private members** | Prefix with `_` (e.g., `_build_ssh_cmd()`) |

### 8.3 Import Organization

```python
# 1. Standard library
import os
from typing import Dict, Any

# 2. Third-party
import pytest

# 3. Local
from library.functions import TestLogger
from library.vars.common_vars import CMDS
from library.messages import TEST_NAMES, ASSERT_MSGS
```

### 8.4 Shell Scripts

- Start with `set -euo pipefail`
- Use functions for reusable logic
- Support `--help` flag

---

## 9. Pylint Rules

### 9.1 Score Requirements

- **CI threshold**: 8.0/10 (automated gate — PR fails below this)
- **Team standard**: 8.8/10 minimum per file (code review rejects below this)
- **Current omnia-auto score**: 9.62/10

### 9.2 Running Pylint

```bash
# Activate the venv first (omnia-auto must be installed)
source .venv/bin/activate

# Check a single file
pylint library/functions/<domain_name>_func.py

# Check all module files
pylint library/functions/*.py library/vars/*.py library/messages/*.py

# Check the omnia-auto plugin (from test/plugins/)
cd ../plugins && pylint omnia_auto/
```

### 9.3 Do NOT Suppress Warnings

**Do NOT use `# noqa` or `# pylint: disable=...` to suppress warnings.** Fix the actual issue:

| Issue | Fix |
|-------|-----|
| `C0301` line-too-long | Break long strings, use variables |
| `R0913` too-many-arguments | Group related params into a dict or dataclass |
| `R0914` too-many-locals | Extract helper functions |
| `R0912` too-many-branches | Use lookup dicts, early returns |
| `W0611` unused-import (re-exports) | Add `__all__` to declare public API |
| `W0613` unused-argument | Prefix with `_` (e.g., `_host`) |
| `C0114/C0115/C0116` missing-docstring | Add docstrings to every module/class/function |

Only `# pylint: disable` is acceptable for `global-statement` where truly needed.

---

## 10. Bandit Security Rules

### 10.1 Running Bandit

```bash
# Scan all module code
bandit -r library/ -ll -ii

# Scan omnia-auto plugin
cd ../plugins && bandit -r omnia_auto/ -ll -ii
```

### 10.2 Rules

- **No High severity issues** — these block the PR.
- **Medium severity** — must be reviewed and justified.
- `shell=True` subprocess calls: Add `# nosec B602` with a comment explaining why.
- Never hardcode passwords (`B105`) — use `load_test_credentials()`.
- No hardcoded `/tmp/` paths (`B108`) — if it is a remote SSH path, add `# nosec B108` with justification.

---

## 11. Security Rules

### 11.1 No Hardcoded Secrets

- **Never commit real IPs, passwords, hostnames, or tokens.**
- `test_config.yml` must ship with `oim_server_ip: ""` — user fills in locally.
- `test_creds.yml` must ship with `oim_password: ""` — user fills in locally.
- Credentials file is auto-encrypted with Ansible Vault on first run.

### 11.2 Pre-Push Security Scan

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

## 12. CI Checks (All Must Pass)

The following CI workflows run on every PR. **All must pass before merge.**

| Check | Tool | Rule |
|-------|------|------|
| **DCO** | `dco` | Every commit signed off (`git commit -s`) |
| **Pylint** | `pylint` | Score ≥ 8.0 per file (CI may report `import-error` for `omnia_auto` — expected) |
| **Bandit** | `bandit` | No High severity issues |
| **Gitleaks** | `gitleaks` | No secrets in committed code |
| **Ansible Lint** | `ansible-lint` | YAML best practices (`true`/`false` not `yes`/`no`, newline at EOF) |
| **pip-audit** | `pip-audit` | No vulnerable Python dependencies |
| **Checkmarx** | SAST | No hardcoded credentials, no insecure file operations |

---

## 13. Environment Setup and Testing

### 13.1 Setup (One-Time)

```bash
cd test/<domain_name>/

# Step 1: Run setup script to create venv and install dependencies
bash setup_env.sh

# Step 2: Activate the virtual environment
source .venv/bin/activate

# Step 3: Configure test settings
vi test_config.yml        # Set oim_server_ip, paths, options
vi test_creds.yml         # Set oim_password (auto-encrypted on first run)
```

`setup_env.sh` installs all dependencies from `requirements.txt` (including `omnia-auto`
from `../plugins/dist/omnia_auto-1.0.0-py3-none-any.whl`).

### 13.2 Running Tests — Use `run_validation`, NOT `pytest`

**Always use `run_validation` (or `./run_validation.sh`) to run tests.** Never invoke `pytest` directly.

```bash
# Verify a specific scenario
run_validation <scenario> verify --marker sanity

# Deploy + verify
run_validation <domain_name> test

# Run a specific suite within a scenario
run_validation <scenario> verify --suite <suite_name>

# Full batch from config
run_validation --config

# List available scenarios
run_validation list
```

### 13.3 Test Iteration Loop

```
Write code → Run tests → Fix failures → Re-run tests → All pass → Push
                ↑                              |
                └──────────────────────────────┘
```

**Never push with known failures. Never skip a failing test to "fix later".**

---

## 14. Feature Testing Workflow

### 14.1 Writing Tests for a New Feature

```
1. Read the playbook source code (src/<domain_name>/)
2. Identify what resources the playbook creates
3. Manually verify on a working cluster
4. Check omnia_auto for existing verification functions
5. Write domain-specific verification function in <domain_name>_func.py
6. Write the test in fvt/<scenario>/<suite>/
7. Add messages to <domain_name>_msgs.py
8. Add TC ID to fvt/TEST_CASES.md
9. Run pylint + bandit + tests
10. Push
```

### 14.2 Rebuilding the `omnia-auto` Wheel

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
cd ../image_build_manager/      # or your domain module
source .venv/bin/activate
pip install --force-reinstall ../plugins/dist/omnia_auto-1.0.0-py3-none-any.whl

# 5. Verify the install
python -c "import omnia_auto; print(omnia_auto.__version__)"
```

---

## 15. Git Commit Rules (MANDATORY)

### 15.1 Commit Format

```bash
git commit --signoff \
  --author="Your Name <your.email@dell.com>" \
  -m "<type>(<scope>): <description>"
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### 15.2 Commit Message Rules

- **First line**: `<type>(<scope>): <description>` (max 72 chars)
- **Body** (optional): Blank line, then details in bullet points
- **Signed-off-by**: Auto-added by `--signoff` flag

```
feat(repo_manager): add prepare phase verification tests

- Add TC_PR_001 through TC_PR_005 for prepare tag tests
- Add check_repo_container_running function
- Update TEST_NAMES and ASSERT_MSGS

Signed-off-by: Your Name <your.email@dell.com>
```

### 15.3 Branch Naming

```
feature/<issue>-<short-description>
bugfix/<issue>-<short-description>
```

### 15.4 PR Description

1. **Title**: Clear, concise summary
2. **Issues Resolved**: Link with `Fixes #<number>`
3. **Description**: What was done, what was tested, results
4. **Do NOT reference file paths** in PR descriptions — describe functionality

---

## 16. Full Pre-Push Verification Checklist

Run this sequence before every push:

```bash
source .venv/bin/activate

# 1. Pylint — all changed files must score ≥ 8.8
pylint library/functions/*.py library/vars/*.py library/messages/*.py

# 2. Bandit — no High severity
bandit -r library/ -ll -ii

# 3. Gitleaks — no secrets
grep -rn -iE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' \
    --include="*.py" --include="*.yml" | \
    grep -v '127\.0\.0\.1' | grep -v '0\.0\.0\.0'

# 4. Run tests — all must pass
run_validation <scenario> verify --marker sanity

# 5. Only push when everything is green
git commit -s -m "<type>(<scope>): description"
git push
```

---

## 17. Quality Checklist

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
- [ ] Use dynamic inputs (no hardcoded IPs, paths, ports)
- [ ] Google-style docstrings with Args/Returns
- [ ] Shell commands in `CMDS` dict — none inline

### Messages
- [ ] `TEST_NAMES`, `LOG_MSGS`, `ASSERT_MSGS` defined in `messages/`
- [ ] No inline strings in test files
- [ ] All messages use `{placeholder}` syntax

### Tests
- [ ] Module docstring lists all test cases with TC IDs
- [ ] Every test function docstring starts with `TC_XX_NNN:`
- [ ] Every test uses `TestLogger` and calls `tl.passed()` / `tl.failed()`
- [ ] Deploy tests have `@pytest.mark.order(0)`
- [ ] All imports from `library.functions` — never from `omnia_auto` directly
- [ ] TC IDs match entries in `fvt/TEST_CASES.md`

### Code Quality
- [ ] `pylint` score ≥ 8.8 for all changed files
- [ ] `bandit -r library/ -ll -ii` shows no High severity issues
- [ ] No `# noqa` or `# pylint: disable` (fix the actual issue)

### Security
- [ ] `test_config.yml` has no real IPs or passwords
- [ ] `test_creds.yml` ships with empty values
- [ ] `.gitignore` excludes `.test_creds.key`, `.venv/`, `__pycache__/`, `reports/`
- [ ] No secrets in committed files

### Git
- [ ] Commit signed off (`git commit -s`)
- [ ] `requirements.txt` references `../plugins/dist/omnia_auto-1.0.0-py3-none-any.whl`
- [ ] Copyright header on all new source files
