# Test Automation — Coding Rules

> Adapted from [Dell Omnia Automation Framework Rules](https://github.com/dell/omnia-containers).
> All test automation code under `test/` MUST follow these rules.

---

## 1. Module Architecture

### 1.1 Directory Structure (MANDATORY)

```
test/
├── fvt/                            # Functional Verification Tests
│   ├── <scenario>/                 # One folder per test scenario
│   │   ├── deploy/test_deploy.py   # Playbook execution (deploy command)
│   │   ├── <component>/test_<component>.py
│   │   └── ...
│   └── <domain>/                   # Full verification (verify command)
│       ├── <component>/
│       ├── <component>/
│       └── ...
├── library/                        # Shared automation library
│   ├── functions/                  # Verification logic
│   │   ├── __init__.py
│   │   ├── <domain>_func.py        # Domain-specific checks
│   │   ├── host_func.py            # Connection, sync, config loading
│   │   ├── formatting_func.py      # TestLogger, Colors, Symbols
│   │   ├── runner_func.py          # PlaybookRunner
│   │   └── report_func.py          # TestReport, HTML generation
│   ├── vars/                       # Constants and configuration
│   │   ├── __init__.py
│   │   ├── common_vars.py          # CMDS dict, paths, ports, retries
│   │   └── runner_vars.py          # PlaybookRunner constants
│   ├── messages/                   # All user-facing strings
│   │   ├── __init__.py
│   │   └── <domain>_msgs.py        # TEST_NAMES, LOG, ASSERT, SKIP
│   └── validation/                 # Config validation
│       └── functions/
│           └── validation_func.py
├── datasets/                       # Input datasets
│   └── <dataset>/
│       ├── config.yml              # Top-level project config
│       └── input/                  # Files synced to target
│           ├── <domain>_config.yml
│           ├── <domain>_credentials.yml
│           └── upstream_output/
├── conftest.py                     # pytest hooks and fixtures
├── test_config.yml                 # Server connection and sync settings
├── test_run_config.yml             # Suite enable/disable and markers
├── test_creds.yml                  # SSH credentials (vault-encrypted)
├── run_validation.sh               # Main entry point
├── setup_env.sh                    # Environment setup script
└── requirements.txt                # Python dependencies
```

### 1.2 Strict Separation Rules

| Content | Location | Never In |
|---------|----------|----------|
| Shell commands | `CMDS` dict in `common_vars.py` | Test files, function files |
| Test names | `TEST_NAMES` in `build_image_msgs.py` | Test files |
| Log messages | `TEST_LOG_MSGS` in `build_image_msgs.py` | Test files |
| Assert messages | `TEST_ASSERT_MSGS` in `build_image_msgs.py` | Test files |
| Skip messages | `TEST_LOG_MSGS` (skip keys) in `build_image_msgs.py` | Test files |
| Constants | `common_vars.py` or `runner_vars.py` | Function or test files |
| Verification logic | `functions/*.py` | Test files |

### 1.3 `__init__.py` Requirements

Every `__init__.py` MUST:
1. Include Apache 2.0 license header (current year)
2. Provide a module docstring
3. Import and re-export specific items (no `import *`)
4. Group imports: functions, then vars, then messages

---

## 2. Test Writing Rules

### 2.1 Test File Docstring (MANDATORY)

Every test file MUST start with a module docstring listing all test cases:

```python
"""
<Domain Name> — <Component> Verification Tests.

TC_<AREA>_001: Verify <aspect 1>
TC_<AREA>_002: Verify <aspect 2>
TC_<AREA>_003: Verify <aspect 3>
"""
```

### 2.2 Test Function Structure (MANDATORY)

```python
@pytest.mark.x86_64
@pytest.mark.sanity
@pytest.mark.order(6)
def test_registry_images_x86_64(host):
    """TC_IB_006: Verify x86_64 images in registry."""
    # 1. Initialize logger with centralized test name
    tl = TestLogger(TEST_NAMES["registry_images"].format(arch="x86_64"))

    # 2. Call verification function (returns dict)
    result = check_registry_images(host, arch="x86_64")

    # 3. Handle skip (optional features)
    if result.get("skipped"):
        tl.skipped(result["details"])
        pytest.skip(result["details"])

    # 4. Build details string
    details = format_result(result)

    # 5. Log pass or fail
    if result["success"]:
        tl.passed(LOG["registry_images_ok"].format(arch="x86_64"), details)
    else:
        tl.failed(LOG["registry_images_missing"].format(...), details)

    # 6. Assert with centralized message
    assert result["success"], ASSERT["registry_images_missing"].format(...)
```

### 2.3 Test Naming Convention

| Type | Convention | Example |
|------|-----------|---------|
| Test function | `test_<feature>_<aspect>` | `test_registry_images_x86_64` |
| Test file | `test_<component>.py` | `test_registry_images.py` |
| Test case ID | `TC_<AREA>_<SEQ>` | `TC_IB_006` |

### 2.4 Test Case ID Areas

| Area | Prefix | Description |
|------|--------|-------------|
| Validate | `TC_VL_` | Validation tag tests |
| Prepare | `TC_PR_` | Prepare tag tests |
| Build | `TC_BD_` | Build tag tests |
| Cleanup | `TC_CL_` | Cleanup tag tests |
| End-to-End | `TC_E2E_` | Full suite verification |

### 2.5 Test Output Format

Use `✓`/`✗` format with grouping:

```
  ▶ Verify x86_64 images in registry
  ✔ PASS: All x86_64 images found in registry
    │ Registry: abhoim.vm.cluster:5000
    │ ✓ rhel-x86_64-base
    │ ✓ rhel-slurm_node_x86_64
```

### 2.6 Import Structure for Test Files

```python
# Third-party
import pytest

# Local — Functions
from library.functions import TestLogger, check_registry_images

# Local — Messages
from library.messages import (
    TEST_NAMES,
    TEST_LOG_MSGS as LOG,
    TEST_ASSERT_MSGS as ASSERT,
)
```

---

## 3. Functions Module Rules

### 3.1 Return Dictionary Pattern (MANDATORY)

All verification functions MUST return a dict:

```python
def check_something(host) -> Dict[str, Any]:
    """Verify something.

    Returns:
        Dict with 'success', 'error', and component-specific keys.
    """
    return {
        "success": True,       # REQUIRED — bool
        "error": None,         # REQUIRED — None or error string
        "details": "...",      # Human-readable details
        "skipped": False,      # True if feature not configured
    }
```

### 3.2 Dynamic Input Rules (CRITICAL)

**NEVER hardcode:**
- IP addresses or hostnames
- File paths that vary by environment
- Credentials or secrets
- Port numbers (use constants from `common_vars.py`)

**ALWAYS:**
- Read from `test_config.yml` via `load_test_config()`
- Use `CMDS` dict for shell commands
- Use constants from `common_vars.py` for paths and ports

### 3.3 Skip Pattern for Optional Features

```python
if not groups:
    return {
        "success": True,
        "skipped": True,
        "details": f"No {arch} functional groups configured",
    }
```

---

## 4. Variables Module Rules

### 4.1 Command Dictionary (MANDATORY)

All shell commands MUST be in `CMDS`:

```python
CMDS: Dict[str, str] = {
    "check_container": "podman ps --format '{{{{.Names}}}}' --filter name={}",
    "list_s3_objects": "s3cmd ls s3://{bucket}/ --host={host}",
}
```

### 4.2 Constants

```python
# Ports
MINIO_API_PORT = 9000
REGISTRY_PORT = 5000

# Retries
CONTAINER_WAIT_RETRIES = 5
CONTAINER_WAIT_DELAY = 3
```

---

## 5. Messages Module Rules (MANDATORY)

### 5.1 Required Dictionaries

```python
TEST_NAMES: Dict[str, str] = {
    "registry_images": "Verify {arch} images in registry",
}

TEST_LOG_MSGS: Dict[str, str] = {
    "registry_images_ok": "All {arch} images found in registry",
    "build_status_not_found": "build_status.yml not found ...",
}

TEST_ASSERT_MSGS: Dict[str, str] = {
    "registry_images_missing": (
        "REGISTRY IMAGES MISSING\n"
        "...\n"
        "HOW TO FIX:\n"
        "  1. Check registry: regctl repo ls ...\n"
    ),
}
```

### 5.2 Rules
- Use `{placeholder}` for dynamic values
- Include **HOW TO FIX** in assertion messages
- Never hardcode IPs in messages — use `<placeholder>` format

---

## 6. Code Standards

### 6.1 License Header (MANDATORY)

Every Python file MUST start with:

```python
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# ...
```

### 6.2 Python Standards

- Python 3.12+ compatibility
- pylint score ≥ 8.7
- Max line length: 100 characters
- 4-space indentation, no tabs
- Type hints on all public functions
- Google-style docstrings on all functions

### 6.3 Import Organization

```python
# 1. Standard library
import os
from typing import Dict, Any

# 2. Third-party
import pytest

# 3. Local
from library.functions import TestLogger
from library.vars.common_vars import CMDS
from library.messages import TEST_NAMES
```

### 6.4 Shell Scripts

- Start with `set -euo pipefail`
- Use functions for reusable logic
- Support `--help` flag

---

## 7. Git Commit Rules (MANDATORY)

### 7.1 Commit Format

All commits **MUST** use `--signoff` and `--author`:

```bash
git commit --signoff \
  --author="Your Name <your.email@dell.com>" \
  -m "Issue #<number>: Short description of change"
```

**Example:**

```bash
git commit --signoff \
  --author="Your Name <your.email@dell.com>" \
  -m "Issue #42: Add x86_64 S3 image verification tests"
```

### 7.2 Commit Message Rules

- **First line**: `Issue #<number>: <imperative verb> <what changed>` (max 72 chars)
- **Body** (optional): Blank line, then details in bullet points
- **Signed-off-by**: Auto-added by `--signoff` flag

```
Issue #42: Add x86_64 S3 image verification tests

- Add TC_IB_004 and TC_IB_005 for S3 image checks
- Add check_s3_bucket_images function
- Update TEST_NAMES and TEST_LOG_MSGS

Signed-off-by: Your Name <your.email@dell.com>
```

### 7.3 Branch Naming

```
feature/<issue>-<short-description>
bugfix/<issue>-<short-description>
```

### 7.4 Before Push Checklist

- [ ] `pylint score ≥ 8.7` — run `pylint` on all changed files
- [ ] No hardcoded credentials or secrets in code
- [ ] `test_creds.yml` is encrypted (not plain text)
- [ ] Dataset files contain only keys, no actual secret values
- [ ] `.test_creds.key` and `.<domain>_credentials_key` are in `.gitignore`
- [ ] All tests pass: `./run_validation.sh <domain> verify --marker sanity`

---

## 8. Quality Checklist

Before submitting code:

### Module Structure
- [ ] Follows `functions/`, `vars/`, `messages/` structure
- [ ] All `__init__.py` files properly export items
- [ ] License headers in all files (current year)

### Functions
- [ ] Return dicts with `success`, `error` keys
- [ ] Use dynamic inputs (no hardcoded IPs, paths)
- [ ] Docstrings with Args/Returns

### Variables
- [ ] All shell commands in `CMDS` dict
- [ ] All constants in `vars/` directory
- [ ] No magic numbers in functions or tests

### Messages
- [ ] `TEST_NAMES`, `TEST_LOG_MSGS`, `TEST_ASSERT_MSGS` defined
- [ ] Assert messages include HOW TO FIX
- [ ] All messages use `{placeholder}` syntax

### Tests
- [ ] Module docstring lists all test cases with IDs
- [ ] Use `TestLogger` with `tc_id` parameter
- [ ] Skip logic for optional features
- [ ] All messages imported from `messages/`
- [ ] All constants imported from `vars/`
- [ ] pylint score ≥ 8.7

### Git
- [ ] Commit with `--signoff --author`
- [ ] No secrets in committed files
- [ ] Dataset values sanitized (keys only)
