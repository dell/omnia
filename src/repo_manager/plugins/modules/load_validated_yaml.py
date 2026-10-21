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

"""Load runtime YAML only after rejecting Ansible/Jinja template syntax."""

# pylint: disable=import-error,no-name-in-module

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.repo_manager.yaml_safety import (
    YamlSafetyError,
    load_runtime_yaml,
)


DOCUMENTATION = r"""
---
module: load_validated_yaml
short_description: Load literal runtime YAML without Jinja evaluation
description:
  - Parses a runtime YAML file with C(yaml.safe_load).
  - Rejects Jinja expression, statement, and comment delimiters recursively.
  - Returns the same parsed data that was validated.
options:
  path:
    description: Absolute path to the runtime YAML file.
    required: true
    type: path
  required:
    description: Fail when the file does not exist.
    required: false
    type: bool
    default: true
  require_mapping:
    description: Require the YAML document root to be a mapping.
    required: false
    type: bool
    default: true
author:
  - Dell Technologies (@dell)
"""

EXAMPLES = r"""
- name: Load validated Repo Manager configuration
  load_validated_yaml:
    path: "{{ repo_manager_config_file }}"
  register: validated_config
  no_log: true

- name: Load optional validated metadata
  load_validated_yaml:
    path: "{{ omnia_metadata_file }}"
    required: false
  register: validated_metadata
"""

RETURN = r"""
data:
  description: Parsed YAML data after template-syntax validation.
  returned: always
  type: dict
exists:
  description: Whether the requested file exists.
  returned: always
  type: bool
"""


SAFE_ERROR_MESSAGES = {
    "invalid_yaml": "Runtime YAML contains invalid syntax",
    "mapping_required": "Runtime YAML document root must be a mapping",
    "maximum_nesting_depth_exceeded": "Runtime YAML exceeds the supported nesting depth",
    "recursive_alias_forbidden": "Runtime YAML cannot contain recursive aliases",
    "template_syntax_forbidden": (
        "Runtime YAML must contain literal values; Jinja syntax is not allowed"
    ),
    "yaml_read_failed": "Runtime YAML could not be read",
}


def main() -> None:
    """Run the validated runtime-YAML loader."""
    module = AnsibleModule(
        argument_spec={
            "path": {"type": "path", "required": True},
            "required": {"type": "bool", "default": True},
            "require_mapping": {"type": "bool", "default": True},
        },
        supports_check_mode=True,
    )

    try:
        data, exists = load_runtime_yaml(
            module.params["path"],
            required=module.params["required"],
            require_mapping=module.params["require_mapping"],
        )
    except FileNotFoundError:
        module.fail_json(
            msg="Required runtime YAML file was not found",
            error_code="file_not_found",
        )
    except YamlSafetyError as exc:
        module.fail_json(
            msg=SAFE_ERROR_MESSAGES.get(exc.code, "Runtime YAML validation failed"),
            error_code=exc.code,
            error_location=exc.location,
        )

    module.exit_json(changed=False, data=data, exists=exists)


if __name__ == "__main__":
    main()
