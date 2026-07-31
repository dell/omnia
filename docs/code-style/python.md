# Python Style Guide -- Omnia

Based on [Dell Omnia Python Style Guide](https://github.com/dell/omnia), adapted from Google Python Style Guide.

## 1. Environment

| Component | Minimum | Validated |
|-----------|---------|-----------|
| Python | 3.12+ | 3.12.8 |
| pylint score | ≥ 8.0 | — |

## 2. Language Rules

### 2.1 Linting
- Use `pylint` for static analysis — **every Python file MUST score ≥ 8.0**
- CI enforces per-file pylint scoring: files below 8.0 fail the PR gate
- Use `flake8` as secondary checker
- Use `.pylintrc` at repo root to suppress known false positives (e.g., `E0401`/`E0611` for Ansible `module_utils` runtime imports)

### 2.2 Imports
- Standard library first, then third-party, then local
- One import per line
- No wildcard imports (`from module import *`)

### 2.3 Type Annotations
- Type hints on all public functions
- Use `typing` module for complex types

### 2.4 Exceptions
- Catch specific exceptions — never bare `except:`
- Re-raise with context: `raise ... from e`

## 3. Style Rules

### 3.1 Naming
| Type | Convention | Example |
|------|-----------|---------|
| Modules | `snake_case` | `validate_config.py` |
| Functions | `snake_case` | `load_repo_status()` |
| Classes | `PascalCase` | `ImageBuildConfig` |
| Constants | `ALL_CAPS` | `MAX_RETRIES` |
| Private | `_prefix` | `_validate_input()` |

### 3.2 Line Length
- Maximum 100 characters per line

### 3.3 Indentation
- 4 spaces — no tabs

### 3.4 Docstrings
- Google-style docstrings for all public functions/classes
```python
def validate_config(config_path: str) -> dict:
    """Validate and load configuration file.

    Args:
        config_path: Absolute path to config.yml.

    Returns:
        Parsed configuration dictionary.

    Raises:
        FileNotFoundError: If config file does not exist.
    """
```

## 4. Ansible Module Patterns

### 4.1 Module Structure
```python
#!/usr/bin/python
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
# Licensed under the Apache License, Version 2.0

"""Module docstring describing purpose."""

from ansible.module_utils.basic import AnsibleModule


def main():
    """Main module entry point."""
    module = AnsibleModule(
        argument_spec=dict(
            param1=dict(type='str', required=True),
        ),
        supports_check_mode=True,
    )
    # Logic here
    module.exit_json(changed=False, result="ok")


if __name__ == '__main__':
    main()
```

### 4.2 Module Utilities
- Place shared code in `src/module_utils/`
- Import as `from ansible.module_utils.<name> import <function>`

### 4.3 Error Handling
- Use `module.fail_json(msg="...")` for failures — never `sys.exit()`
- Always set `changed=True/False` accurately

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

- All three blocks are **mandatory** — Galaxy rejects modules without any of them.
- `EXAMPLES` MUST use FQCN: `omnia.<collection>.<module>`, not short names.
- `RETURN` MUST document every key returned by `module.exit_json()`.
- Validate locally: `ansible-doc omnia.<collection>.<module>` — if it renders, Galaxy will accept it.
- Use `r'''` (raw triple-quoted strings) to avoid YAML escaping issues.

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

1. **Messages MUST live in `messages/`** — never define error strings inline in validators or flow files. Import from `messages.<module>`.
2. **Messages use `UPPER_SNAKE_CASE`** constants for static strings and `def <name>_msg(...)` functions for parameterized messages.
3. **`core/config.py`** MUST contain ONLY domain-specific constants (file mappings, version maps, path config). Do NOT include constants for other domains.
4. **`validation_engine.py`** routes L2 validation to the correct validator via a dict mapping of filename → validator function. It MUST NOT contain domain-specific logic.
5. **Validators** import from `core.config`, `core.utils`, `core.file_utils`, and `messages.*`. They return a list of error dicts: `{"error_key": str, "error_value": str, "error_msg": str}`.
6. **Schema files** MUST only contain schemas relevant to this domain. Do NOT dump schemas for other domains.
7. **`common/` shared code** (from the legacy monolith) MUST NOT be used by new domains. Each domain owns its validation stack.

### 6.4 Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|-------------|---------|-----------------|
| Inline error strings in validators | Untranslatable, hard to audit, inconsistent | Constants in `messages/` |
| One giant messages file for all domains | 944+ lines, merge conflicts, no ownership | Split: `common_messages.py` + `<domain>_messages.py` |
| Flat validation (no subdirectories) | Unscalable, no separation of concerns | Use `core/`, `messages/`, `schema/`, `validators/` |
| Importing from `common/library/` | Cross-domain coupling, blocks independence | Domain-local `plugins/module_utils/input_validation/` |
| `library/` path for modules | Legacy, breaks Galaxy packaging | Use `plugins/` |

### 6.5 Reference Implementation

The `repo_manager` domain demonstrates the canonical structure. See `src/repo_manager/library/module_utils/input_validation/` (to be migrated to `plugins/module_utils/`).

---

## 7. Security & Quality Gates

All Python code MUST pass the following gates before merge:

| Gate | Tool | Requirement | Enforcement |
|------|------|-------------|-------------|
| **Static Analysis** | `pylint` | Every `.py` file scores ≥ 8.0 | CI per-file check (`.github/workflows/pylint.yml`) |
| **Secret Leak Detection** | `gitleaks` | Zero findings | CI pre-commit / PR gate |
| **SAST** | Checkmarx | Zero High/Critical findings | CI or scheduled scan |
| **Shell Script Lint** | `shellcheck` | Zero errors in `.sh` files | CI lint step |

### 7.1 Pylint Per-File Scoring

- Every Python file changed in a PR is scored individually
- Files scoring below **8.0** fail the PR gate
- Use inline `# pylint: disable=<code>` only for justified false positives (document reason in comment)
- Global disables go in `.pylintrc` at repo root — only for Ansible runtime import false positives

### 7.2 Gitleaks (Secret Leak Prevention)

- No hardcoded passwords, API keys, tokens, or credentials in any source file
- Use Ansible Vault for sensitive values
- Use `.gitleaks.toml` to configure allowlists for known false positives
- CI runs `gitleaks detect` on every PR

### 7.3 Checkmarx (SAST)

- Zero High or Critical findings allowed in merged code
- Medium findings SHOULD be addressed within the same sprint
- False positives MUST be documented and suppressed via Checkmarx project settings

### 7.4 ShellCheck (Shell Script Lint)

- All `.sh` files (e.g., `copy-input.sh`) MUST pass `shellcheck` with zero errors
- Warnings (SC-level) SHOULD be addressed; suppressions allowed with `# shellcheck disable=SCXXXX` and a justification comment
