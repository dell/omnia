# Omnia Test Automation — Development Rules

Rules and standards for developing test automation modules in the Omnia monorepo.
**All developers must follow these rules strictly.**

---

## 1. Pre-Development Analysis (MANDATORY)

### 1.1 Analyze the Source Code First

Before writing **any** automation code:

1. **Clone the omnia monorepo** and read the playbook source code under `src/<module>/`.
2. **Identify all roles** the playbook calls, what hosts it targets, and what resources it creates (containers, services, files, pods, configs).
3. **Map each resource to a verification test** — every container the playbook creates should have a test that checks it is running, every service should be checked as active, etc.

```bash
# Example: analyze image_build_manager
ls src/image_build_manager/playbooks/       # Main playbook entry points
ls src/image_build_manager/roles/           # All roles
cat src/image_build_manager/playbooks/prepare.yml  # Read prepare phase
```

### 1.2 Manually Verify on a Working Cluster

If a working cluster is available:

1. **Log into the target server** and manually verify the feature works.
2. **Check containers, services, ports, files** that the playbook creates.
3. **Document what you verified manually** — these become your test cases.
4. **Never automate blind** — if you have not verified it manually at least once, do not write automation for it.

### 1.3 Check the omnia-auto Plugin First

Before writing ANY new function:

1. **Install `omnia-auto` from the local wheel**:
   ```bash
   pip install ../plugins/dist/omnia_auto-1.0.0-py3-none-any.whl
   python -c "import omnia_auto; print(omnia_auto.__all__)"
   ```
2. **Read the API reference**: [`test/plugins/USAGE.md`](../plugins/USAGE.md) and [`test/plugins/docs/`](../plugins/docs/)
3. **Search for existing functions** that do what you need — SSH connection, file sync, config loading, host connection, playbook execution, formatting, reporting.
4. **Only write a new function if no existing function in `omnia-auto` covers it.**
5. If your new function could be reused across modules, propose adding it to `test/plugins/omnia_auto/` instead of keeping it module-local, then rebuild the wheel.

---

## 2. Code Standards

### 2.1 Pylint Score

- **Minimum score: 8.8/10** per file.
- Run pylint from the module's virtual environment (where `omnia-auto` is installed):
  ```bash
  .venv/bin/pylint library/functions/my_func.py
  ```
- **Do NOT use `# noqa` or `# pylint: disable=...` to suppress warnings.**
  Fix the actual issue instead:
  - `unused-import` on re-exports → use `__all__` to declare public API
  - `import-error` → add the package to `requirements.txt`
  - `unused-argument` → use `_` prefix (e.g., `_host`) for intentionally unused params
  - `wrong-import-position` → move all imports to the top of the file
  - `too-many-branches` → refactor into smaller helper functions
- If pylint is failing, **fix the code and re-run** until it passes. Do not push code below 8.8.

### 2.2 Docstrings

Every function must have a docstring explaining:

- **What** it does (one-line summary)
- **Parameters** (if not obvious from type hints)
- **Returns** (structure of the return dict/value)

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

### 2.3 Test Case IDs and Naming

Every test function must:

1. Have a **TC ID** in the docstring: `TC_<PHASE>_<NNN>` (e.g., `TC_PR_001`, `TC_VL_002`).
2. Use a **descriptive test name** prefixed with `test_`:
   ```python
   def test_registry_after_prepare(host):
       """TC_PR_003: Verify container registry is running after prepare."""
   ```
3. Use `TestLogger` for structured output:
   ```python
   tl = TestLogger("Verify registry is running", "TC_PR_003")
   ```

### 2.4 Use omnia-auto Functions, Not Raw Commands

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

### 2.5 Module Structure

Follow the standard directory structure (reference: `test/image_build_manager/`):

```
test/<module_name>/
├── conftest.py                    # Session setup, omnia_auto.configure()
├── test_config.yml                # Non-sensitive settings (IP, paths)
├── test_creds.yml                 # Sensitive credentials (auto-encrypted)
├── requirements.txt               # Dependencies including omnia-auto
├── datasets/                      # Custom test datasets (optional)
│   └── generator/                 # Dataset generator tool
├── library/
│   ├── functions/
│   │   ├── __init__.py            # Public API — imports from omnia_auto + local
│   │   ├── <module>_func.py       # Module-specific verification functions
│   │   ├── host_func.py           # Sync functions, re-exports from omnia_auto
│   │   └── validation_func.py     # Config validation
│   ├── vars/
│   │   └── common_vars.py         # Constants (container names, paths, services)
│   └── messages/
│       └── <module>_msgs.py       # Test names, log messages, assertion messages
└── fvt/
    ├── prepare/                   # Prepare phase tests
    ├── build/                     # Build phase tests
    ├── validate/                  # Validation tests
    └── cleanup/                   # Cleanup verification tests
```

### 2.6 Re-exports with `__all__`

When importing from `omnia_auto` for consumer convenience (re-exporting):

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
    "my_module_function",
]
```

This is the standard Python way to declare public API — pylint and other tools respect `__all__`.

### 2.7 Strict Rules for Variables and Commands (MANDATORY)

**Every constant, path, and shell command MUST live in `library/vars/common_vars.py`.**
Violating these rules will block code review.

#### 2.7.1 No Hardcoded Paths in Function or Test Files

| Violation | Correct |
|-----------|---------|
| `"/tmp/ibm_test_image"` inline | `IMAGE_VERIFY_TEMP_IMAGE` in `common_vars.py` |
| `"/opt/omnia/repo_manager/output"` inline | `REPO_MANAGER_OUTPUT_PATH` in `common_vars.py` |
| `"functional_group_packages.yml"` inline | `FG_PACKAGES_FILENAME` in `common_vars.py` |
| `"squashfs-tools"` inline | `SQUASHFS_PACKAGE` in `common_vars.py` |

**Rule:** If a string literal represents a filesystem path, package name, container
name, port number, bucket name, or service name — it MUST be a named constant in
`common_vars.py`, exported from `vars/__init__.py`, and imported where needed.

#### 2.7.2 No Inline Shell Commands in Function or Test Files

All shell commands executed via `host.run()` MUST use the `CMDS` dictionary in
`common_vars.py`.

| Violation | Correct |
|-----------|---------|
| `host.run(f"cat {path} 2>/dev/null")` | `host.run(CMDS["cat_file"].format(path=path))` |
| `host.run(f"dnf install -y squashfs-tools")` | `host.run(CMDS["squashfs_tools_install"].format(package=SQUASHFS_PACKAGE))` |
| `host.run(f"mount -t squashfs -o ro {img} {mnt}")` | `host.run(CMDS["mount_squashfs"].format(image=img, mount=mnt))` |
| `host.run(f"podman ps --format ... --filter ...")` | `host.run(CMDS["podman_ps_running"].format(container=name))` |

**Rule:** Never write a raw shell command string inside `host.run()`. Always
add the command template to `CMDS` with descriptive named placeholders, then
call `CMDS["key"].format(...)` at the call site.

#### 2.7.3 No Hardcoded Validation Constants

Regex patterns, required field lists, and required file lists used in
`validation_func.py` MUST be defined in `common_vars.py`:

```python
# In common_vars.py:
IPV4_PATTERN = re.compile(r'...')
REQUIRED_CONFIG_FIELDS = ["dataset", "project_name", ...]
REQUIRED_DATASET_FILES = ["input/image_build_config.yml", ...]

# In validation_func.py:
from ..vars.common_vars import IPV4_PATTERN, REQUIRED_CONFIG_FIELDS, REQUIRED_DATASET_FILES
```

#### 2.7.4 Adding a New Command or Constant — Checklist

When you need a new shell command or constant:

1. **Add the constant** to `common_vars.py` with a descriptive comment.
2. **Add the export** to `vars/__init__.py`.
3. **Import it** in the function file that uses it.
4. **Use `.format()` with named placeholders** — never positional `%s` or f-string interpolation inside CMDS values.
5. **Verify with `python -c "from library.vars import CMDS; print(CMDS['new_key'])"`.

#### 2.7.5 CMDS Naming Convention

| Category | Prefix | Example |
|----------|--------|---------|
| Podman | `podman_` | `podman_ps_running`, `podman_inspect` |
| S3/s3cmd | `s3cmd_` | `s3cmd_ls`, `s3cmd_get` |
| Registry | `curl_registry_`, `regctl_` | `curl_registry_catalog_scheme` |
| File operations | descriptive | `cat_file`, `file_exists`, `rm_file`, `mkdir_p` |
| System | descriptive | `hostname_cmd`, `rpm_check`, `which_cmd` |
| Systemd | `systemctl_` | `systemctl_is_active` |
| Squashfs | `squashfs_` | `squashfs_tools_check`, `squashfs_tools_install` |
| Mount | `mount_`, `umount` | `mount_squashfs`, `umount` |

#### 2.7.6 Pre-Commit Verification

Before committing, run this check to detect violations:

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

## 2.8 Test Case Registry (`TEST_CASES`) Rules

All test case metadata (TC ID, title) **must** be defined in `library/vars/test_case_vars.py`
and referenced via `TEST_CASES["key"]` in test files.

### Rules

| Rule | Allowed | Forbidden |
|------|---------|-----------|
| TC ID source | `TC["key"]["id"]` | Hardcoded `"TC_IB_006"` in test code |
| Title source | `TC["key"]["title"]` | `TEST_NAMES["key"]` or hardcoded string |
| TestLogger init | `TestLogger(tc["title"], tc["id"])` | `TestLogger("...", "TC_IB_006")` |
| Docstring comments | Description only (no TC IDs) | `"""TC_IB_006: Verify ...` |
| Playbook name | `run_playbook(playbook=PLAYBOOK_ENTRY_POINT, ...)` | `run_playbook(tag="prepare")` without playbook |

### Standard Test Function Pattern

```python
from library.vars import TEST_CASES as TC
from library.vars.common_vars import PLAYBOOK_ENTRY_POINT

tc = TC["deploy_prepare"]
tl = TestLogger(tc["title"], tc["id"])
result = run_playbook(playbook=PLAYBOOK_ENTRY_POINT, tag="prepare")
```

### Verification

```bash
# Must return zero results:
grep -rn '"TC_[A-Z]*_[0-9]' fvt/ --include="*.py" | grep -v __pycache__ | grep -v test_case_vars
```

---

## 3. CI Checks (All Must Pass)

The following CI workflows run on every PR. **All must pass before merge.**

### 3.1 DCO (Developer Certificate of Origin)

Every commit must have a `Signed-off-by` line:

```bash
git commit -s -m "feat: description of change"
```

Format: `Signed-off-by: Your Name <your.email@dell.com>`

### 3.2 Pylint (`pylint.yml`)

- Runs on all changed `.py` files (excluding `__init__.py`).
- **Threshold: 8.0** (CI), **target: 8.8+** (team standard).
- Run pylint locally from the activated venv (where `omnia-auto` is installed) to get accurate scores.
- The CI may report `import-error` for `omnia_auto` — this is expected since CI does not install it.
  As long as the score stays above 8.0 in CI and above 8.8 in the venv, it passes.

### 3.3 Bandit Security Scan (`bandit.yml`)

- Runs Bandit SAST on changed Python files with `-ll -ii` (Medium+ severity, Medium+ confidence).
- Common issues:
  - `B108` (hardcoded `/tmp/`) — if it is a remote SSH path, add `# nosec B108` with justification.
  - `B105` (hardcoded passwords) — never hardcode passwords; use `load_test_credentials()`.

### 3.4 Secret Leak Scan (`gitleaks.yml`)

- Scans for hardcoded secrets, passwords, tokens, API keys.
- **No real IPs, passwords, or tokens** in committed code.
- Use empty placeholders: `oim_server_ip: ""`, `oim_password: ""`.
- In documentation, use angle-bracket placeholders: `<SSH_PASSWORD>`, `<SERVER_IP>`.
- Gitleaks rule: `generic-password` triggers on `password: "value"` where value ≥ 8 chars.

### 3.5 Ansible Lint (`ansible-lint.yml`)

- Runs on all changed `.yml`/`.yaml` files.
- Common issues:
  - `yaml[new-line-at-end-of-file]` — always end YAML files with a single newline.
  - `yaml[empty-lines]` — no consecutive blank lines; max 1 blank line at end.
  - `yaml[truthy]` — use `true`/`false`, not `yes`/`no`.

### 3.6 Dependency Vulnerability Scan (`pip-audit.yml`)

- Runs `pip-audit` on dependencies.
- Keep `requirements.txt` packages up to date.

### 3.7 Checkmarx (External)

- Code must pass Checkmarx SAST scan.
- No hardcoded credentials, no SQL injection patterns, no insecure file operations.

---

## 4. Security Rules

### 4.1 No Hardcoded Secrets

- **Never commit real IPs, passwords, hostnames, or tokens.**
- `test_config.yml` must ship with `oim_server_ip: ""` — user fills in locally.
- `test_creds.yml` must ship with `oim_password: ""` — user fills in locally.
- Credentials file is auto-encrypted with Ansible Vault on first run.

### 4.2 Pre-Push Security Scan

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

## 5. Environment Setup and Testing

### 5.1 Setup (One-Time)

Before running any tests, the developer must set up the environment:

```bash
cd test/<module_name>/

# Step 1: Run setup script to create venv and install dependencies
bash setup_env.sh

# Step 2: Activate the virtual environment
source .venv/bin/activate

# Step 3: Configure test settings
vi test_config.yml        # Set oim_server_ip, paths, options
vi test_creds.yml         # Set oim_password (auto-encrypted on first run)
```

**The venv must be active before running any tests.** `setup_env.sh` installs all
dependencies from `requirements.txt` (including `omnia-auto` from the local wheel
at `../plugins/dist/omnia_auto-1.0.0-py3-none-any.whl`) and registers the
`run_validation` command with tab-completion.

### 5.2 Running Tests — Use `run_validation`, NOT `pytest`

**Always use `run_validation` (or `./run_validation.sh`) to run tests.** Never invoke
`pytest` directly.

```bash
# Verify a specific scenario
run_validation prepare verify --marker sanity
run_validation validate verify --marker sanity
run_validation build verify --marker sanity
run_validation cleanup verify

# Run a specific suite within a scenario
run_validation prepare verify --suite container
run_validation build verify --suite s3

# Full end-to-end (deploy + verify)
run_validation image_build_manager test

# List available scenarios
run_validation list
```

`run_validation` handles venv activation, pytest configuration, report generation,
and structured summary output automatically.

### 5.3 Watch the Full Output

- **Do NOT use `tail`, `head`, or output redirection** while verifying automation.
- The developer must see the complete test execution flow from start to finish.
- The structured output (TC IDs, PASS/FAIL, duration, summary table) is designed
  to give a clear picture of what ran and what the results are.

### 5.4 Test Iteration Loop — Fix Until Clean

After writing or modifying any automation code:

1. Run the full test suite using `run_validation`.
2. If any test fails — **fix the issue**.
3. Re-run the tests.
4. Repeat until **all tests pass**.
5. **Do not push until every test is green.**

```
Write code → Run tests → Fix failures → Re-run tests → All pass → Push
                ↑                              |
                └──────────────────────────────┘
```

Never break this loop. Never push with known failures. Never skip a failing test
to "fix later".

---

## 6. PR and Commit Standards

### 6.1 Commit Messages

Use conventional commits with DCO signoff:

```
<type>(<scope>): <description>

<optional body>

Signed-off-by: Your Name <your.email@dell.com>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### 6.2 PR Description

Every PR must include:

1. **Title**: Clear, concise summary (e.g., `feat(image_build_manager): add prepare phase verification`)
2. **Issues Resolved**: Link to the issue with `Fixes #<number>`
3. **Description**: What the PR does, what was tested, results summary
4. **Do NOT reference file paths** in PR descriptions — describe functionality, not files.

Bad: "Updated `library/functions/build_image_func.py` to fix S3 check"
Good: "Fixed S3 bucket verification to handle empty bucket list gracefully"

### 6.3 PR Checklist

Before marking a PR as "Ready for Review":

- [ ] All CI checks pass (DCO, Pylint, Bandit, Gitleaks, Ansible Lint, pip-audit)
- [ ] Pylint score ≥ 8.8 for all changed files
- [ ] No hardcoded IPs, passwords, or tokens
- [ ] No `# noqa` or `# pylint: disable` comments (fix properly)
- [ ] All functions have docstrings
- [ ] All test cases have TC IDs
- [ ] Tests run successfully with `run_validation.sh`
- [ ] Code uses `omnia-auto` functions where available
- [ ] Copyright header present on all new files

---

## 7. Copyright Header

Every new file must start with the Apache 2.0 copyright header:

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

---

## 8. Pylint and Bandit Verification Workflow

### 8.1 Pylint — Run Before Every Push

Every changed Python file must be checked with pylint before committing:

```bash
# Activate the venv first
source .venv/bin/activate

# Check a single file
pylint library/functions/build_image_func.py

# Check all module files
pylint library/functions/*.py library/vars/*.py library/messages/*.py

# Check the omnia-auto plugin (from test/plugins/)
cd ../plugins && pylint omnia_auto/
```

**Score requirements:**
- **CI threshold**: 8.0/10 (automated gate — PR will fail below this)
- **Team standard**: 8.8/10 (code review will reject below this)
- **Current omnia-auto score**: 9.62/10

**Common pylint fixes:**

| Issue | Fix |
|-------|-----|
| `C0301` line-too-long | Break long strings, use variables |
| `R0913` too-many-arguments | Group related params into a dict or dataclass |
| `R0914` too-many-locals | Extract helper functions |
| `R0912` too-many-branches | Use lookup dicts, early returns |
| `W0611` unused-import (re-exports) | Add `__all__` to declare public API |
| `W0613` unused-argument | Prefix with `_` (e.g., `_host`) |
| `C0114/C0115/C0116` missing-docstring | Add docstrings to every module/class/function |

### 8.2 Bandit — Security Scan Before Every Push

```bash
# Scan all module code
bandit -r library/ -ll -ii

# Scan omnia-auto plugin
cd ../plugins && bandit -r omnia_auto/ -ll -ii
```

**Rules:**
- **No High severity issues** — these block the PR
- **Medium severity** — must be reviewed and justified
- **Low severity** — informational, acceptable for subprocess usage in automation
- `shell=True` subprocess calls: Add `# nosec B602` with a comment explaining why
- Never hardcode passwords — use `load_test_credentials()`

### 8.3 Full Pre-Push Verification Checklist

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
run_validation prepare verify --marker sanity
run_validation validate verify --marker sanity
run_validation image_build_manager verify --marker sanity

# 5. Only push when everything is green
git commit -s -m "feat: description"
git push
```

---

## 9. Feature Testing Workflow

### 9.1 Writing Tests for a New Feature

When a new Omnia playbook feature is added, follow this workflow:

```
1. Read the playbook source code (src/<domain>/)
2. Identify what resources the playbook creates
3. Manually verify on a working cluster
4. Map each resource to a verification function
5. Write the verification function in <domain>_func.py
6. Write the test in fvt/<scenario>/<suite>/
7. Add messages to <domain>_msgs.py
8. Run pylint + bandit + tests
9. Push
```

### 9.2 Test Structure Pattern

Every test file follows this pattern:

```python
import pytest
from library.functions import TestLogger, check_something
from library.messages import TEST_NAMES, ASSERT_MSGS

@pytest.mark.sanity
@pytest.mark.order(1)
def test_something(host):
    """TC_XX_NNN: Verify something works after deployment."""
    tl = TestLogger(TEST_NAMES["something"], "TC_XX_NNN")
    result = check_something(host)
    tl.passed(result["details"]) if result["success"] else tl.failed(result["error"])
    assert result["success"], ASSERT_MSGS["something_failed"]
```

### 9.3 Deploy Test Pattern

Deploy tests use `run_playbook()` with live output streaming:

```python
import pytest
from library.functions import run_playbook, TestLogger

@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.order(0)
def test_deploy_scenario(host):
    """TC_XX_000: Deploy <domain> --tags <tag>."""
    tl = TestLogger("Deploy <scenario>", "TC_XX_000")
    result = run_playbook(tag="<tag>", timeout=3600)
    tl.passed("Playbook completed") if result["success"] else tl.failed(result["error"])
    assert result["success"], result["error"]
```

### 9.4 Rebuilding the omnia-auto Wheel

If you modify the shared plugin code in `test/plugins/omnia_auto/`:

```bash
cd ../plugins/

# 1. Run pylint on the plugin
pylint omnia_auto/

# 2. Run bandit
bandit -r omnia_auto/

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
