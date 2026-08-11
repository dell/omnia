# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
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

# pylint: disable=unused-import,line-too-long
#!/usr/bin/python

DOCUMENTATION = r'''
---
module: validate_credentials

short_description: Validate credential inputs against defined rules

version_added: "2.2.0"

description:
    - This module validates credential field inputs against predefined validation rules.
    - It checks length requirements, pattern matching, and other constraints defined in the schema.
    - Returns validation success or failure with detailed error messages.

options:
    credential_field:
        description:
            - The name of the credential field to validate.
            - Must match a field name defined in the credential_rules.json schema.
        required: true
        type: str
    credential_input:
        description:
            - The actual credential value to validate against the rules.
            - This value will be checked for length, pattern, and other constraints.
        required: true
        type: str
    module_utils_path:
        description:
            - Path to the module_utils directory containing the input_validation schema.
            - If not provided, uses a default path structure.
        required: false
        type: str
        default: null

author:
    - Dell Technologies Omnia Team

requirements:
    - python >= 3.12
    - Access to credential_rules.json schema file
'''

EXAMPLES = r'''
# Validate BMC username input
- name: Validate BMC username
  validate_credentials:
    credential_field: "bmc_username"
    credential_input: "{{ bmc_username }}"
    module_utils_path: "/path/to/module_utils"
  register: username_validation

# Validate password with default path
- name: Validate BMC password
  validate_credentials:
    credential_field: "bmc_password"
    credential_input: "{{ bmc_password }}"
  register: password_validation

# Use validation result in conditional task
- name: Proceed with credential usage
  ansible.builtin.debug:
    msg: "Credentials validated successfully"
  when: username_validation is succeeded and password_validation is succeeded
'''

RETURN = r'''
msg:
    description: Validation result message indicating success or failure details
    type: str
    returned: always
    sample: "bmc_username is valid"

changed:
    description: Whether the module made any changes (always false for this validation module)
    type: bool
    returned: always
    sample: false

failed:
    description: Whether the validation failed
    type: bool
    returned: failure
    sample: true
'''

""" This module is used to validate credentials"""

import json
import os
import re
from typing import Tuple, Dict, Any

from ansible.module_utils.basic import AnsibleModule


def load_rules(file_path: str) -> Dict[str, Any]:
    """Loads validation rules from a JSON file.
    
    Args:
        file_path: Path to the JSON rules file
        
    Returns:
        Dictionary containing validation rules
        
    Raises:
        FileNotFoundError: If the rules file doesn't exist
        json.JSONDecodeError: If the JSON is invalid
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def validate_input(field: str, value: str, rules: Dict[str, Any]) -> Tuple[bool, str]:
    """Validates input against rules.
    
    Args:
        field: The credential field name
        value: The credential value to validate
        rules: Dictionary of validation rules
        
    Returns:
        Tuple of (success_flag, validation_message)
    """
    if field not in rules:
        return (False, f"Validation rules not found for '{field}'")
    rule = rules[field]
    if not rule["minLength"] <= len(value) <= rule["maxLength"]:
        return (False, f"'{field}' length must be between {rule['minLength']} and {rule['maxLength']} characters")
    if "pattern" in rule and not re.match(rule["pattern"], value):
        return (False, f"'{field}' format is invalid. Description: {rule['description']}")
    return (True, f"'{field}' is valid")

def main():
    """Main module function."""
    module_args = {
        "credential_field": {"type": "str", "required": True},
        "credential_input": {"type": "str", "required": True},
        "module_utils_path": {"type": "str", "required": False, "default": None}
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    params = module.params
    module_utils_base = module.params["module_utils_path"]
    credentials_schema = os.path.join(module_utils_base,'input_validation','schema',\
                                      'credential_rules.json')
    # Load validation rules
    try:
        rules = load_rules(credentials_schema)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
        module.fail_json(msg=f"Failed to load rules: {e}")

    # Validate credential
    credential_valid, credential_msg = validate_input(params["credential_field"], \
                                                      params["credential_input"], rules)

    if credential_valid:
        module.exit_json(changed=False, msg=f"{credential_msg}")
    else:
        module.fail_json(msg=f"Validation failed: {credential_msg}")

if __name__ == "__main__":
    main()
