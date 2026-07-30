#!/usr/bin/python
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

"""Ansible module to validate YAML files against JSON Schema."""

import json
from typing import Any, Dict

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import jsonschema
    from jsonschema import Draft7Validator
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

from ansible.module_utils.basic import AnsibleModule


DOCUMENTATION = r'''
---
module: validate_yaml_schema
short_description: Validate YAML file against JSON Schema
description:
  - Validates a YAML file against a JSON Schema definition
  - Returns validation errors if schema validation fails
options:
  yaml_file:
    description: Path to YAML file to validate
    required: true
    type: str
  schema_file:
    description: Path to JSON Schema file
    required: true
    type: str
'''

EXAMPLES = r'''
- name: Validate config.yml against schema
  validate_yaml_schema:
    yaml_file: /path/to/config.yml
    schema_file: /path/to/config.schema.json
'''


def load_yaml_file(file_path: str) -> Dict[str, Any]:
    """Load YAML file and return parsed content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_json_schema(file_path: str) -> Dict[str, Any]:
    """Load JSON Schema file and return parsed content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_against_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> tuple:
    """Validate data against schema.
    
    Returns:
        tuple: (is_valid: bool, errors: list)
    """
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    
    if errors:
        error_messages = []
        for error in errors:
            path = '.'.join(str(p) for p in error.path) if error.path else 'root'
            error_messages.append(f"{path}: {error.message}")
        return False, error_messages
    
    return True, []


def main():
    """Main module entry point."""
    module = AnsibleModule(
        argument_spec=dict(
            yaml_file=dict(type='str', required=True),
            schema_file=dict(type='str', required=True),
        ),
        supports_check_mode=True,
    )

    if not HAS_YAML:
        module.fail_json(msg="PyYAML library is required for this module")

    if not HAS_JSONSCHEMA:
        module.fail_json(msg="jsonschema library is required for this module")

    yaml_file = module.params['yaml_file']
    schema_file = module.params['schema_file']

    try:
        # Load YAML data
        yaml_data = load_yaml_file(yaml_file)
        
        # Load JSON Schema
        schema = load_json_schema(schema_file)
        
        # Validate
        is_valid, errors = validate_against_schema(yaml_data, schema)
        
        if is_valid:
            module.exit_json(
                changed=False,
                msg="YAML file is valid against schema",
                valid=True
            )
        else:
            module.fail_json(
                msg=f"YAML validation failed: {'; '.join(errors)}",
                errors=errors,
                valid=False
            )
    
    except FileNotFoundError as e:
        module.fail_json(msg=f"File not found: {e}")
    except yaml.YAMLError as e:
        module.fail_json(msg=f"YAML parsing error: {e}")
    except json.JSONDecodeError as e:
        module.fail_json(msg=f"JSON schema parsing error: {e}")
    except Exception as e:
        module.fail_json(msg=f"Unexpected error: {e}")


if __name__ == '__main__':
    main()
