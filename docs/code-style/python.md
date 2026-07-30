# Python Style Guide — Image Build Manager

Based on [Dell Omnia Python Style Guide](https://github.com/dell/omnia), adapted from Google Python Style Guide.

## 1. Environment

| Component | Minimum | Validated |
|-----------|---------|-----------|
| Python | 3.12+ | 3.12.8 |
| pylint score | ≥ 8.0 | — |

## 2. Language Rules

### 2.1 Linting
- Use `pylint` for static analysis — target score ≥ 8.0
- Use `flake8` as secondary checker

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
