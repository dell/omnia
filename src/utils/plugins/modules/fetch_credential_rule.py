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

#!/usr/bin/python

DOCUMENTATION = r'''
---
module: fetch_credential_rule

short_description: Fetch validation rules for credential fields

version_added: "2.2.0"

description:
    - This module retrieves validation rules for credential fields from a JSON schema file.
    - It provides rule descriptions that can be used for input validation and user guidance.
    - Primarily used for fetching credential validation rules in Omnia workflows.

options:
    credential_field:
        description:
            - The name of the credential field to fetch validation rules for.
            - Must match a field name defined in the credential_rules.json schema.
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
# Fetch validation rule for BMC username field
- name: Get BMC username validation rule
  fetch_credential_rule:
    credential_field: "bmc_username"
    module_utils_path: "/path/to/module_utils"
  register: username_rule

# Fetch validation rule for password field
- name: Get password validation rule
  fetch_credential_rule:
    credential_field: "bmc_password"
  register: password_rule

# Display the rule description
- name: Show rule description
  ansible.builtin.debug:
    msg: "{{ password_rule.msg }}"
'''

RETURN = r'''
msg:
    description: The validation rule description for the requested credential field
    type: str
    returned: success
    sample: "BMC username must be 3-16 characters, alphanumeric with underscores allowed"

changed:
    description: Whether the module made any changes (always false for this read-only module)
    type: bool
    returned: always
    sample: false

failed:
    description: Whether the module failed to execute
    type: bool
    returned: failure
    sample: false
'''

"""This module is used to fetch credential rules."""

import json
import os
from pathlib import Path
from typing import Tuple, Dict, Any

from ansible.module_utils.basic import AnsibleModule

try:
    from ansible_collections.omnia.utils.plugins.module_utils.security_utils import validate_file_path
except ImportError:
    # Fallback for development/testing
    def validate_file_path(file_path: str, allowed_base_dirs=None) -> Tuple[bool, str]:
        """Fallback validation if security_utils not available"""
        if not file_path:
            return False, "File path cannot be empty"
        if '..' in file_path:
            return False, "File path cannot contain '..'"
        return True, ""

def load_rules(file_path: str) -> Dict[str, Any]:
    """Loads validation rules from JSON file.
    
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

def fetch_rule(field: str, rules: Dict[str, Any]) -> Tuple[bool, str]:
    """Fetches validation rule for a given field.
    
    Args:
        field: The credential field name to look up
        rules: Dictionary of validation rules
        
    Returns:
        Tuple of (success_flag, description_message)
    """
    if field not in rules:
        return (False, f"No validation rules found for '{field}'")

    rule = rules[field]
    return (True, rule.get("description", "No description available"))

def main():
    """Main function."""
    module_args = {
        "credential_field": {"type": "str", "required": True},
        "module_utils_path": {"type": "str", "required": False, "default": None}
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    params = module.params
    module_utils_base = module.params["module_utils_path"]
    
    # Validate module_utils_path for security (path traversal and command injection)
    path_valid, path_error = validate_file_path(module_utils_base)
    if not path_valid:
        module.fail_json(msg=f"Invalid module_utils_path: {path_error}")
    
    # Construct and validate credentials schema path
    try:
        credentials_schema = Path(module_utils_base) / 'input_validation' / 'schema' / 'credential_rules.json'
        credentials_schema = credentials_schema.resolve()
        
        # Validate resolved path for security
        path_valid, path_error = validate_file_path(str(credentials_schema))
        if not path_valid:
            module.fail_json(msg=f"Invalid schema path after resolution: {path_error}")
    except (ValueError, RuntimeError) as e:
        module.fail_json(msg=f"Failed to resolve schema path: {str(e)}")
    
    # Load validation rules
    try:
        rules = load_rules(str(credentials_schema))
    except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
        module.fail_json(msg=f"Failed to load rules: {e}")

    # Fetch and return rule description
    success, message = fetch_rule(params["credential_field"], rules)
    if success:
        module.exit_json(changed=False, msg=message)
    else:
        module.fail_json(msg=message)

if __name__ == "__main__":
    main()
