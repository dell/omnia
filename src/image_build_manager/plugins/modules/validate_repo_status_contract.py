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

"""Validate the repo_manager output contract before image build setup."""

import logging
import os

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.input_validation.core.file_utils import (
    load_json,
    load_yaml,
)
from ansible.module_utils.input_validation.core.validation_engine import (
    logic_repo_status,
    schema,
)

DOCUMENTATION = r'''
---
module: validate_repo_status_contract
short_description: Validate repo_status.yml for image build execution
version_added: "2.3.0"
description:
  - Validates the repo_status.yml contract produced by repo_manager.
  - Applies the complete JSON Schema and image-build semantic checks.
  - Intended for build and execute flows, before repo_status.yml is parsed.
options:
  repo_status_file:
    description: Absolute path to repo_status.yml.
    required: true
    type: str
  schema_file:
    description: Absolute path to the repo_status JSON Schema.
    required: true
    type: str
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Validate repo manager output contract
  omnia.image_build.validate_repo_status_contract:
    repo_status_file: /opt/omnia/repo_manager/output/project_default/repo_status.yml
    schema_file: /opt/omnia/image_build_manager/plugins/module_utils/input_validation/schema/repo_status.json
'''

RETURN = r'''
errors:
  description: Contract violations. Empty when validation succeeds.
  returned: always
  type: list
  elements: str
'''


def validate_contract(repo_status_file, schema_file, logger=None):
    """Return all schema and semantic errors for repo_status.yml."""
    validation_logger = logger or logging.getLogger(__name__)
    errors = []

    if not os.path.isfile(repo_status_file):
        return [f"repo_status.yml not found: {repo_status_file}"]
    if not os.path.isfile(schema_file):
        return [f"repo_status schema not found: {schema_file}"]

    repo_status_data = load_yaml(repo_status_file)
    if not isinstance(repo_status_data, dict):
        return [f"repo_status.yml is not a valid YAML object: {repo_status_file}"]

    schema_definition = load_json(schema_file)
    if not isinstance(schema_definition, dict):
        return [f"repo_status schema is not a valid JSON object: {schema_file}"]

    schema(
        repo_status_data,
        schema_definition,
        "repo_status.yml",
        errors,
        validation_logger,
    )
    if not errors:
        errors.extend(logic_repo_status(repo_status_data, validation_logger))
    return errors


def main():
    """Run the Ansible module."""
    module = AnsibleModule(
        argument_spec={
            "repo_status_file": {"type": "path", "required": True},
            "schema_file": {"type": "path", "required": True},
        },
        supports_check_mode=True,
    )

    errors = validate_contract(
        module.params["repo_status_file"],
        module.params["schema_file"],
    )
    if errors:
        module.fail_json(
            msg="repo_status.yml contract validation failed",
            errors=errors,
            changed=False,
        )
    module.exit_json(changed=False, errors=[])


if __name__ == "__main__":
    main()
