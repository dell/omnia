# Python Style Guide -- Omnia

Based on [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), adapted for Omnia project conventions.

## 0. Environment

| Component | Minimum | Validated |
|-----------|---------|-----------|
| Python | 3.12+ | 3.12.8 |
| pylint | latest | CI enforced |
| RHEL | 10.0+ | 10.0 |

## 1. Python Language Rules

- **Linting:** Run `pylint` on your code. CI threshold: **score >= 8.0** (from `PYLINT_THRESHOLD=8`)
- **Imports:** Use `import x` for packages/modules. Use `from x import y` only when `y` is a submodule. Group: standard library -> third-party -> local.
- **Exceptions:** Prefer built-in exception classes when appropriate. Domain-specific exceptions MAY be used when they improve error handling clarity. Custom exceptions MUST inherit from `Exception` (not `BaseException`). Do not use bare `except:` clauses. Always catch specific exceptions.

```python
# Built-in exception — preferred for common cases
raise ValueError("Invalid architecture: expected x86_64 or aarch64")

# Domain-specific exception — acceptable when it adds clarity
class CatalogParseError(Exception):
    """Raised when the software catalog cannot be parsed."""

raise CatalogParseError(f"Malformed catalog entry at index {idx}")

# WRONG — bare except catches KeyboardInterrupt, SystemExit
try:
    data = json.loads(raw)
except:
    pass

# CORRECT — catch specific exceptions
try:
    data = json.loads(raw)
except (json.JSONDecodeError, TypeError) as exc:
    module.fail_json(msg=f"Invalid JSON: {exc}")
```

- **Global State:** Avoid mutable global state. Module-level constants are okay and MUST be `ALL_CAPS_WITH_UNDERSCORES`.
- **Comprehensions:** Use for simple cases. Avoid for complex logic where a full loop is more readable.
- **Default Argument Values:** Do not use mutable objects (like `[]` or `{}`) as default values.
- **True/False Evaluations:** Use implicit false (e.g., `if not my_list:`). Use `if foo is None:` to check for `None`.
- **Type Annotations:** Required for all public functions. Strongly encouraged for all code.
- **No Wildcard Imports:** Never use `from module import *`.

## 2. Python Style Rules

- **Line Length:** Maximum **100** characters.
- **Indentation:** 4 spaces per indentation level. Never use tabs.
- **Blank Lines:** Two blank lines between top-level definitions (classes, functions). One blank line between method definitions.
- **Whitespace:** Avoid extraneous whitespace. Surround binary operators with single spaces.
- **Docstrings:** Use `"""triple double quotes"""`. Every public module, function, class, and method MUST have a docstring.
  - **Format:** Google-style with `Args:`, `Returns:`, and `Raises:` sections.
- **Strings:** Use f-strings for formatting. Be consistent with quote style.
- **`TODO` Comments:** Use `TODO(ticket-id): description` format. Reference a Jira or issue tracker ID, not a personal username.

```python
# CORRECT
# TODO(OMNIA-1234): Refactor to use async SSH for better throughput
# TODO(GH-567): Add retry logic for transient DNS failures

# AVOID
# TODO(john): Fix this later
# TODO: something
```

## 3. Naming

- **General:** `snake_case` for modules, functions, methods, and variables.
- **Classes:** `PascalCase`.
- **Constants:** `ALL_CAPS_WITH_UNDERSCORES`.
- **Internal Use:** Use a single leading underscore (`_internal_variable`) for internal module/class members.

## 4. Main & Module Structure

### 4.1 Executable Scripts
All executable files SHOULD have a `main()` function called from `if __name__ == '__main__':`.

### 4.2 Ansible Module Structure
Custom Ansible modules live in `plugins/modules/`:
```python
#!/usr/bin/python
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
# Licensed under the Apache License, Version 2.0

"""Module docstring describing purpose."""

from ansible.module_utils.basic import AnsibleModule
```

### 4.3 Module Utils
Shared utilities in `plugins/module_utils/<component>/`:
- `__init__.py` -- Package marker
- `config.py` -- Constants and configuration
- `common_functions.py` -- Shared helper functions

### 4.4 Module-First Data Processing
Core logic SHOULD be in standalone functions (testable without Ansible).
`main()` SHOULD only wire `AnsibleModule` params to core functions.
See Ansible Style Guide §12 for when to prefer modules over Jinja2.

### 4.5 Docstring Format
Use Google-style docstrings:
```python
def load_json_file(path: str, module: AnsibleModule) -> dict | None:
    """Load a JSON file safely.

    Args:
        path: Path to the JSON file.
        module: The Ansible module instance.

    Returns:
        Parsed JSON content if successful, None otherwise.

    Raises:
        FileNotFoundError: If path does not exist.
    """
```

### 4.6 CI Dependencies
Pylint CI installs these packages for import resolution:
```
ansible pylint kubernetes prettytable requests passlib
fastapi uvicorn sqlalchemy pytest httpx argon2-cffi
pyyaml dependency-injector
```

Set `PYTHONPATH=.:./build_stream` when running pylint locally.

**BE CONSISTENT.** When editing code, match the existing style.

## 5. Ansible Galaxy Module Documentation (REQUIRED)

Every Python module under `plugins/modules/*.py` MUST contain three documentation constants for Galaxy import compliance. Galaxy import **fails** without them.

### 5.1 Required Blocks

| Block | Purpose | Placement |
|-------|---------|-----------|
| `DOCUMENTATION` | Module name, description, options, author | After imports, before first function |
| `EXAMPLES` | Playbook task examples showing usage | After `DOCUMENTATION` |
| `RETURN` | Return value documentation with types | After `EXAMPLES` |

### 5.2 Template

```python
#!/usr/bin/python
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
# Licensed under the Apache License, Version 2.0

"""Module docstring describing purpose."""

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
---
module: my_module
short_description: One-line summary of the module
version_added: "3.0.0"
description:
  - Detailed description of what the module does.
  - Can span multiple list items.
options:
  param_name:
    description: What this parameter controls.
    required: true
    type: str
  optional_param:
    description: Optional parameter with default.
    required: false
    type: int
    default: 0
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Example task using FQCN
  omnia.image_build.my_module:
    param_name: value
  register: result

- name: Display result
  ansible.builtin.debug:
    var: result
'''

RETURN = r'''
output_key:
  description: What this return value contains.
  returned: always
  type: str
'''


def main():
    """Main module entry point."""
    module = AnsibleModule(
        argument_spec=dict(
            param_name=dict(type='str', required=True),
        ),
        supports_check_mode=True,
    )
    module.exit_json(changed=False, output_key="ok")


if __name__ == '__main__':
    main()
```

### 5.3 Rules

- All three blocks are **mandatory** -- Galaxy rejects modules without any of them.
- `EXAMPLES` MUST use FQCN: `omnia.<collection>.<module>`, not short names.
- `RETURN` MUST document every key returned by `module.exit_json()`.
- Validate locally: `ansible-doc omnia.<collection>.<module>`.
- Use `r'''` (raw triple-quoted strings) to avoid YAML escaping issues.
- `version_added` MUST reflect the actual collection version where the module was introduced. Do not copy placeholder values from examples.

### 5.4 Anti-Patterns

| Anti-Pattern | Why It Fails | Fix |
|-------------|-------------|-----|
| Missing `DOCUMENTATION` | Galaxy import rejects the module | Add `DOCUMENTATION` constant |
| Short module name in `EXAMPLES` | Galaxy validator warns | Use FQCN: `omnia.<coll>.<mod>` |
| `sys.exit()` in module | Ansible loses error context | Use `module.fail_json(msg=...)` |
| Logic in `main()` | Untestable without Ansible | Extract to standalone functions |
| Mutable default arguments | Shared state across calls | Use `None` + conditional init |

### 5.5 Reference Implementation

```python
#!/usr/bin/python
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
# Licensed under the Apache License, Version 2.0

"""Parse a software catalog JSON and return structured package data."""

from __future__ import annotations

import json
from typing import Any
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
---
module: parse_catalog
short_description: Parse software catalog JSON into structured package lists
version_added: "3.0.0"
description:
  - Reads a JSON catalog file and extracts packages filtered by architecture.
  - Replaces complex Jinja2 set_fact logic with testable Python.
options:
  catalog_file:
    description: Path to the catalog JSON file.
    required: true
    type: str
  build_arch:
    description: Target architecture (x86_64 or aarch64).
    required: true
    type: str
    choices: [x86_64, aarch64]
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Parse catalog
  omnia.image_build.parse_catalog:
    catalog_file: /opt/omnia/catalog.json
    build_arch: x86_64
  register: catalog_result

- name: Display packages
  ansible.builtin.debug:
    var: catalog_result.packages
'''

RETURN = r'''
packages:
  description: List of package dicts matching the architecture.
  returned: always
  type: list
'''


def parse_catalog(catalog_path: str, arch: str) -> list[dict[str, Any]]:
    """Parse catalog and filter by architecture.

    Args:
        catalog_path: Path to the JSON catalog.
        arch: Target architecture.

    Returns:
        List of package dicts.
    """
    with open(catalog_path, encoding="utf-8") as fh:
        data = json.load(fh)
    return [pkg for pkg in data.get("packages", []) if arch in pkg.get("arch", [])]


def main():
    """Ansible module entry point."""
    module = AnsibleModule(
        argument_spec=dict(
            catalog_file=dict(type="str", required=True),
            build_arch=dict(type="str", required=True, choices=["x86_64", "aarch64"]),
        ),
        supports_check_mode=True,
    )
    try:
        packages = parse_catalog(module.params["catalog_file"], module.params["build_arch"])
        module.exit_json(changed=False, packages=packages)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        module.fail_json(msg=str(exc))


if __name__ == "__main__":
    main()
```

---

## 6. Input Validation Module Structure

Every domain that validates user-supplied configuration MUST follow the **four-directory** input validation pattern under `plugins/module_utils/input_validation/`.

### 6.1 Canonical Layout

```
plugins/module_utils/input_validation/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── config.py              # Domain-specific constants, paths, mappings
│   ├── file_utils.py          # File reading, YAML/JSON parsing, line-number lookup
│   ├── utils.py               # create_error_msg(), create_file_path(), helpers
│   └── validation_engine.py   # L1 schema + L2 logic orchestration & routing
├── messages/
│   ├── __init__.py
│   ├── common_messages.py     # Shared validation messages (log formatting, generic errors)
│   └── <domain>_messages.py   # Domain-specific validation messages
├── schema/
│   ├── __init__.py
│   └── *.json                 # Domain-scoped JSON Schema files (Draft-7)
└── validators/
    ├── __init__.py
    └── <config>_validator.py  # One file per config file being validated (L2 logic)
```

### 6.2 Directory Responsibilities

| Directory | Purpose | Key Rules |
|-----------|---------|-----------|
| `core/` | Engine, config, file I/O | `validation_engine.py` exposes `schema()` and `logic()` entry points; `config.py` contains ONLY domain-specific constants |
| `messages/` | All user-facing error/warning strings | **NEVER** inline error messages in validator or flow code; use `UPPER_SNAKE_CASE` constants; group with `# ====` section headers |
| `schema/` | JSON Schema files for L1 validation | One `.json` per input config file; use Draft-7; domain-scoped only |
| `validators/` | Per-config L2 business-logic validators | One Python file per config file; each exposes a `validate()` function; import messages from `messages/` |

### 6.3 Rules

1. **Messages MUST live in `messages/`** -- never define error strings inline in validators or flow files. Import from `messages.<module>`.
2. **Messages use `UPPER_SNAKE_CASE`** constants for static strings and `def <name>_msg(...)` functions for parameterized messages.
3. **`core/config.py`** MUST contain ONLY domain-specific constants (file mappings, version maps, path config). Do NOT include constants for other domains.
4. **`validation_engine.py`** routes L2 validation to the correct validator via a dict mapping of filename -> validator function. It MUST NOT contain domain-specific logic.
5. **Validators** import from `core.config`, `core.utils`, `core.file_utils`, and `messages.*`. They return a list of error dicts: `{"error_key": str, "error_value": str, "error_msg": str}`.
6. **Schema files** MUST only contain schemas relevant to this domain. Do NOT dump schemas for other domains.
7. **`common/` shared code** (from the legacy monolith) MUST NOT be used by new domains. Each domain owns its validation stack.

### 6.4 Validation Error Structure

Prefer structured error returns using `TypedDict` or `dataclass`:

```python
from dataclasses import dataclass


@dataclass
class ValidationError:
    """Structured validation error returned by validators."""

    error_key: str
    error_value: str
    error_msg: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dict for Ansible module output."""
        return {
            "error_key": self.error_key,
            "error_value": self.error_value,
            "error_msg": self.error_msg,
        }
```

Alternatively, use `TypedDict` when the data is primarily dict-shaped (e.g., for JSON serialization or Ansible module output):

```python
from typing import TypedDict


class ValidationErrorDict(TypedDict):
    """Dict-shaped validation error for Ansible module output."""

    error_key: str
    error_value: str
    error_msg: str
```

**When to use which:**
- `dataclass` -- when you need methods, default values, or `__eq__`/`__repr__`
- `TypedDict` -- when the data must remain a plain dict (e.g., passed to `module.exit_json()`)

For existing code that returns anonymous dicts, maintain consistency within the file but prefer the structured approach for new validators.

### 6.5 Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|-------------|---------|-----------------|
| Inline error strings in validators | Untranslatable, hard to audit, inconsistent | Constants in `messages/` |
| One giant messages file for all domains | 944+ lines, merge conflicts, no ownership | Split: `common_messages.py` + `<domain>_messages.py` |
| Flat validation (no subdirectories) | Unscalable, no separation of concerns | Use `core/`, `messages/`, `schema/`, `validators/` |
| Importing from `common/library/` | Cross-domain coupling, blocks independence | Domain-local `plugins/module_utils/input_validation/` |
| `library/` path for modules | Legacy, breaks Galaxy packaging | Use `plugins/` |

### 6.6 Reference Implementation

The `repo_manager` domain demonstrates the canonical structure. See `src/repo_manager/library/module_utils/input_validation/` (to be migrated to `plugins/module_utils/`).

---

## 7. Security & Quality Gates

All Python code MUST pass the following gates before merge:

| Gate | Tool | Requirement | Enforcement |
|------|------|-------------|-------------|
| **Static Analysis** | `pylint` | Every `.py` file scores >= 8.0 | CI per-file check (`.github/workflows/pylint.yml`) |
| **Python SAST** | `bandit` | Zero High/Critical findings | CI PR gate |
| **Secret Leak Detection** | `gitleaks` | Zero findings | CI pre-commit / PR gate |
| **Dependency CVE** | `pip-audit` | Zero known vulnerabilities | CI PR gate |
| **SAST** | Checkmarx | Zero High/Critical findings | CI or scheduled scan |
| **Code Quality** | SonarQube | Zero bugs/vulns (Blocker/Critical) | Scheduled / release gate |

### 7.1 Pylint Per-File Scoring

- Every Python file changed in a PR is scored individually
- Files scoring below **8.0** fail the PR gate
- Use inline `# pylint: disable=<code>` only for justified false positives (document reason in comment)
- Global disables go in `.pylintrc` at repo root -- only for Ansible runtime import false positives

### 7.2 Secret Logging Prevention

Never log, print, or include in error messages:
- Passwords or passphrases
- API keys or tokens
- Certificates or private keys
- Authentication headers
- SSH keys

```python
# WRONG — logs the password
logger.info("Connecting with password: %s", password)
module.fail_json(msg=f"Auth failed for {user}:{password}")

# CORRECT — redact sensitive values
logger.info("Connecting as user: %s", user)
module.fail_json(msg=f"Authentication failed for user: {user}")
```

### 7.3 Gitleaks (Secret Leak Prevention)

- No hardcoded passwords, API keys, tokens, or credentials in any source file
- Use Ansible Vault for sensitive values
- Use `.gitleaks.toml` to configure allowlists for known false positives
- CI runs `gitleaks detect` on every PR

### 7.4 Checkmarx (SAST)

- Zero High or Critical findings allowed in merged code
- Medium findings SHOULD be addressed within the same sprint
- False positives MUST be documented and suppressed via Checkmarx project settings

### 7.5 ShellCheck (Shell Script Lint)

- All `.sh` files (e.g., `domain-init.sh`) MUST pass `shellcheck` with zero errors
- Warnings (SC-level) SHOULD be addressed; suppressions allowed with `# shellcheck disable=SCXXXX` and a justification comment

---

## 8. HPC Production Scale Rules (1000-Node Clusters)

### 8.1 Threading for Multi-Node Operations

Modules expected to operate on hundreds or thousands of hosts MUST use bounded concurrency. `ThreadPoolExecutor` is the approved default concurrency model for HPC-scale operations.

Small-scale operations (< 20 hosts) are not required to use threading. Standard Ansible modules remain the preferred default.

**Required pattern for HPC-scale modules:**

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_module():
    module = AnsibleModule(argument_spec={
        "hosts": {"type": "list", "required": True, "elements": "str"},
        "ssh_max_parallel": {"type": "int", "default": 20},
        "ssh_connect_timeout": {"type": "int", "default": 10},
    }, supports_check_mode=True)

    hosts = module.params["hosts"]
    max_parallel = module.params["ssh_max_parallel"]

    if module.check_mode:
        module.exit_json(changed=len(hosts) > 0)

    payload = build_payload(module.params)

    result = {"changed": False, "succeeded": [], "failed": [], "per_host": {}}

    with ThreadPoolExecutor(max_workers=min(max_parallel, len(hosts))) as pool:
        futures = {pool.submit(process_host, h, payload): h for h in hosts}
        for future in as_completed(futures):
            host = futures[future]
            try:
                success, stdout, stderr = future.result()
                result["per_host"][host] = {
                    "success": success, "stdout": stdout, "stderr": stderr
                }
                (result["succeeded"] if success else result["failed"]).append(host)
            except Exception as exc:
                result["per_host"][host] = {"success": False, "stderr": str(exc)}
                result["failed"].append(host)

    result["changed"] = len(result["succeeded"]) > 0
    if result["failed"]:
        module.warn(
            f"Failed on {len(result['failed'])} host(s): "
            f"{', '.join(result['failed'])}"
        )
    module.exit_json(**result)
```

### 8.2 SSH Execution Best Practices

When executing remote commands via `subprocess.run()`:

```python
def _ssh_run(host: str, script: str, ssh_key_path: str, timeout: int) -> tuple:
    cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", f"ConnectTimeout={timeout}",
        "-o", "BatchMode=yes",
        "-o", "LogLevel=ERROR",
        "-i", ssh_key_path,
        f"root@{host}",
        "bash -s",
    ]
    try:
        result = subprocess.run(
            cmd,                      # List args (no shell injection)
            input=script,             # Pass script via stdin
            capture_output=True,
            text=True,
            timeout=timeout + 30,     # Hard timeout > connect timeout
            check=False,              # Handle errors manually
        )
        return (host, result.returncode == 0, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (host, False, "", f"SSH timeout after {timeout + 30}s")
```

**SSH Host Key Verification Note:** `StrictHostKeyChecking=no` and `UserKnownHostsFile=/dev/null` are allowed **only** during controlled provisioning workflows where the OIM manages node identity. Production systems SHOULD honor host key validation policies whenever feasible.

**Rules:**
- ALWAYS use `subprocess.run()` with **list args** -- NEVER `shell=True` (Checkmarx OS Command Injection)
- ALWAYS set `timeout` to prevent hung SSH connections
- ALWAYS use `check=False` and handle errors manually
- ALWAYS cap `max_workers` with `min(ssh_max_parallel, len(hosts))`
- Use `BatchMode=yes` to prevent SSH password prompts from hanging

### 8.3 Checkmarx-Safe Patterns

| Checkmarx Issue | Unsafe Code | Safe Code |
|-----------------|-------------|-----------|
| OS Command Injection | `os.system(f"cmd {user_input}")` | `subprocess.run(["cmd", user_input], check=True)` |
| OS Command Injection | `subprocess.run(cmd, shell=True)` | `subprocess.run(cmd_list, shell=False)` |
| Code Injection | `exec(code_string)` | Avoid; use structured dispatch |
| Insecure YAML Load | `yaml.load(data)`, `yaml.full_load(data)` | `yaml.safe_load(data)` |
| Unsafe YAML Loader | `Loader=yaml.UnsafeLoader`, `Loader=yaml.FullLoader` | `Loader=yaml.SafeLoader` or `yaml.safe_load()` |
| Path Traversal | `open(f"/dir/{user_input}")` | Validate with `os.path.realpath()` + explicit check (see below) |
| Hardcoded Credentials | `password = "admin123"` | `password = module.params["vault_password"]` |
| Insecure Deserialization | `eval(data)` or `pickle.loads(data)` | `json.loads(data)` |
| SQL Injection | `f"SELECT * WHERE id={uid}"` | Parameterized queries |
| Log Injection | `logger.info(f"User: {user_input}")` | Sanitize before logging |

**Path traversal validation pattern:**
```python
import os

ALLOWED_BASE = "/opt/omnia/data"

def safe_open(user_path: str) -> str:
    """Resolve and validate a user-supplied path against an allowlist."""
    resolved = os.path.realpath(os.path.join(ALLOWED_BASE, user_path))
    if not resolved.startswith(ALLOWED_BASE + os.sep):
        raise ValueError(f"Path traversal blocked: {user_path}")
    return resolved
```

Do not use `assert` for security validation -- assertions can be disabled with `python -O`.

### 8.4 SonarQube-Clean Patterns

| SonarQube Issue | Rule | Fix |
|-----------------|------|-----|
| Cognitive Complexity > 15 | `python:S3776` | Break into smaller functions |
| Duplicate string literal | `python:S1192` | Extract to constant |
| Broad exception | `python:S5754` | Catch specific: `except (FileNotFoundError, PermissionError)` |
| Unused variable | `python:S1481` | Remove or prefix with `_` |
| Empty except | `python:S2737` | Log or re-raise |
| Mutable default arg | `python:S5765` | Use `None` + `if arg is None: arg = []` |

### 8.5 Performance Anti-Patterns

| Anti-Pattern | Impact at 1000 Nodes | Fix |
|-------------|---------------------|-----|
| Serial SSH loop | 30+ minutes | ThreadPoolExecutor (1-2 minutes) |
| Building payload per host | O(N) redundant work | Build once, distribute N times |
| No connection timeout | Hung connections block all threads | Set `ConnectTimeout` + hard timeout |
| `max_workers=len(hosts)` | 1000 threads = resource exhaustion | Cap at 20-50 workers |
| Failing entire play on 1 host failure | Cluster partially unusable | Use `module.warn()`, report per-host |
| Gathering all facts on 1000 hosts | 5+ minutes of fact collection | `gather_facts: false`, selective `setup:` |

---

## 9. Logging

### 9.1 Standard

- Use Python `logging` module for applications, services, libraries, and shared utilities
- Avoid `print()` in reusable code (`plugins/`, `module_utils/`)
- `print()` is acceptable only for CLI output (e.g., `omnia-cli`) or temporary local debugging
- For Ansible modules, use `module.warn()`, `module.log()`, `module.fail_json()`, and `module.exit_json()` -- not `print()` or `logging`
- Ansible modules SHOULD NOT instantiate Python logging handlers unless there is a documented requirement
- Avoid mixing Python `logging` and Ansible module logging in the same component

```python
import logging

logger = logging.getLogger(__name__)

def process_hosts(hosts: list[str]) -> dict:
    """Process host list and return results."""
    logger.info("Processing %d hosts", len(hosts))
    for host in hosts:
        logger.debug("Checking host: %s", host)
    return {"processed": len(hosts)}
```

### 9.2 Log Levels

| Level | When to Use |
|-------|------------|
| `DEBUG` | Detailed diagnostic info (not shown in production) |
| `INFO` | Confirmation of normal operations |
| `WARNING` | Something unexpected but recoverable |
| `ERROR` | An error that prevents a specific operation |
| `CRITICAL` | A fatal error that stops the program |

---

## 10. Testing

### 10.1 Framework and Coverage

- **pytest** is the standard unit testing framework
- Public functions SHOULD have unit tests
- Business logic SHOULD be testable independently from Ansible (extract from `main()`)
- New modules SHOULD maintain at least **70% coverage**
- Tests live in `test/<domain>/` mirroring the source structure

### 10.2 Test Structure
```python
# test/image_build_manager/test_parse_catalog.py
import pytest
from parse_catalog import parse_catalog


def test_parse_catalog_filters_by_arch(tmp_path):
    """Verify that parse_catalog filters packages by architecture."""
    catalog = tmp_path / "catalog.json"
    catalog.write_text('{"packages": [{"name": "pkg1", "arch": ["x86_64"]}]}')
    result = parse_catalog(str(catalog), "x86_64")
    assert len(result) == 1
    assert result[0]["name"] == "pkg1"


def test_parse_catalog_empty_on_mismatch(tmp_path):
    """Verify empty result when no packages match."""
    catalog = tmp_path / "catalog.json"
    catalog.write_text('{"packages": [{"name": "pkg1", "arch": ["aarch64"]}]}')
    result = parse_catalog(str(catalog), "x86_64")
    assert result == []
```

---

## 11. Type Checking

Type annotations are required for all public functions (§1). To maximize their value:

- **mypy** or **pyright** are recommended for static type analysis
- Type hints are required for public functions; strongly encouraged for internal functions
- Python 3.12 natively supports `str | None` union syntax without imports
- `from __future__ import annotations` is recommended when using forward references or reducing import-time evaluation overhead -- it is not required solely for union syntax
- Use `typing.TypedDict` or `dataclasses.dataclass` for structured data (see §6.4)

```python
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class HostResult:
    """Result of a remote operation on a single host."""

    hostname: str
    success: bool
    stdout: str = ""
    stderr: str = ""
```

---

## 12. Path Handling

- Prefer `pathlib.Path` for new code
- Use `os.path` only when required for compatibility with existing APIs

```python
from pathlib import Path

# PREFERRED — pathlib
config_path = Path("/opt/omnia") / "config" / "omnia_config.yml"
if config_path.exists():
    content = config_path.read_text(encoding="utf-8")

# ACCEPTABLE — os.path (for compatibility)
import os
config_path = os.path.join("/opt/omnia", "config", "omnia_config.yml")
if os.path.exists(config_path):
    with open(config_path, encoding="utf-8") as fh:
        content = fh.read()
```

---

## 13. Dataclasses

Use `dataclasses.dataclass` for structured data containers instead of plain dicts when the structure is known and repeated:

```python
from dataclasses import dataclass, field


@dataclass
class NodeSpec:
    """Specification for a compute node."""

    hostname: str
    ip_address: str
    cpus: int
    memory_mb: int
    gpu_count: int = 0
    labels: list[str] = field(default_factory=list)
```

Benefits over dicts: type checking, IDE completion, `__repr__`, `__eq__` for free.

---

## 14. Concurrency

### 14.1 Approved Models

| Model | When to Use |
|-------|------------|
| `ThreadPoolExecutor` | **Preferred** for HPC fan-out (SSH to N hosts, parallel file copy) |
| `asyncio` | MAY be used for I/O-heavy workflows (HTTP APIs, database queries) when justified |
| `multiprocessing` | Use only for CPU-bound work that cannot be threaded (GIL-limited) |

### 14.2 Rules

- Do not mix concurrency models within the same component
- Always cap thread/worker count with a configurable parameter
- Always set timeouts on blocking operations
- See §8 for the canonical `ThreadPoolExecutor` pattern

---

## 15. Dependency Management

### 15.1 File Structure

| File | Purpose |
|------|---------|
| `requirements.txt` | Production dependencies (pinned versions) |
| `requirements-dev.txt` | Development/test dependencies (pylint, pytest, mypy, etc.) |
| `constraints.txt` | Version upper bounds for transitive dependencies |

### 15.2 Rules

- Pin production dependencies to specific versions: `requests==2.31.0`
- Dev dependencies may use compatible ranges: `pytest>=7.0,<9.0`
- New dependencies MUST be reviewed for license compatibility (Apache 2.0 compatible)
- New dependencies SHOULD be reviewed for maintenance activity, release stability, security history, and long-term support risk

---

## 16. Cross-References

- **Test co-change rule**: Changes to Python modules (`plugins/modules/`, `module_utils/`) MUST include corresponding UT/FVT test updates -- see `general.md` §6.
- **AI agent policy**: AI agents MUST NOT be used for PR sign-off -- see `general.md` §7.
- **Commit format**: All commits MUST follow `<type>(<scope>): <description>` -- see `general.md` §8.
- **Ansible module-first rule**: Prefer Python modules over Jinja2 for data processing -- see `ansible.md` §12.
- **HPC threading pattern**: Multi-node operations MUST use ThreadPoolExecutor -- see `ansible.md` §13.
- **Jinja2 template scope**: Keep templates thin, move logic to Python -- see `jinja2.md` §7.
