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

# pylint: disable=import-error,no-name-in-module
#!/usr/bin/python

"""
Ansible module for orchestrator-specific input validation.

Performs L1 (JSON schema) and L2 (cross-field logic) validation on:
  - orchestrator_config.yml (required)
  - network_spec.yml        (optional — cross-validated against mapping file)

Usage in a playbook:
  - name: Validate orchestrator configuration
    validate_orchestrator_config:
      input_project_dir: "{{ input_project_dir }}"
      schema_dir: "{{ role_path }}/../../../plugins/module_utils/orchestrator_validation/schema"
"""

import json
import logging
import os

import yaml
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.omnia.orchestrator.plugins.module_utils.orchestrator_validation.orchestrator_validation_flow import (
    validate_orchestrator_config_l2,
    validate_network_spec,
)


DOCUMENTATION = r'''
---
module: validate_orchestrator_config
short_description: Validate orchestrator configuration files
description:
  - Performs L1 (JSON schema) and L2 (cross-field logic) validation on orchestrator_config.yml and network_spec.yml.
options:
  input_project_dir:
    description: Path to the input project directory containing configuration files.
    required: true
    type: str
  schema_dir:
    description: Path to the directory containing JSON schema files.
    required: true
    type: str
'''

EXAMPLES = r'''
- name: Validate orchestrator configuration files
  omnia.orchestrator.validate_orchestrator_config:
    input_project_dir: /opt/omnia/input/project_default
    schema_dir: "{{ role_path }}/../../plugins/module_utils/input_validation/schema"
  register: validation_result
'''

RETURN = r'''
msg:
  description: Validation summary message.
  type: str
  returned: always
validation_errors:
  description: List of validation errors found, if any.
  type: list
  returned: failure
'''

VALIDATION_LOG_PATH = "/opt/omnia/log/core/playbooks/"

# Files to validate and their corresponding schema names
VALIDATION_FILES = [
    {
        "config_file": "orchestrator_config.yml",
        "schema_file": "orchestrator_config.json",
        "required": True,
    },
    {
        "config_file": "network_spec.yml",
        "schema_file": "network_spec.json",
        "required": True,
    },
]


def create_logger(project_name):
    """Create a logger for orchestrator validation."""
    log_file = os.path.join(
        VALIDATION_LOG_PATH, f"orchestrator_validation_{project_name}.log"
    )
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logging.basicConfig(
        filename=log_file,
        format="%(asctime)s %(levelname)s %(message)s",
        filemode="w",
    )
    logger = logging.getLogger("orchestrator_validation")
    logger.setLevel(logging.DEBUG)
    return logger, log_file


VAULT_HEADER = "$ANSIBLE_VAULT"


def is_vault_encrypted(path):
    """Check if a file is Ansible Vault encrypted."""
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
    return first_line.startswith(VAULT_HEADER)


def load_yaml(path):
    """Load a YAML file, returning None on failure."""
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path):
    """Load a JSON file, returning None on failure."""
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_against_schema(data, schema, file_label, errors, logger):
    """
    Validate data against a JSON schema (L1).
    Uses basic type/required/enum checks without jsonschema dependency.
    """
    if not schema or not data:
        return

    schema_type = schema.get("type")
    if schema_type == "object" and not isinstance(data, dict):
        msg = f"{file_label}: Expected object at top level, got {type(data).__name__}"
        errors.append(msg)
        logger.error(msg)
        return

    required = schema.get("required", [])
    properties = schema.get("properties", {})
    for req_key in required:
        if req_key not in data:
            msg = f"{file_label}: Missing required property '{req_key}'"
            errors.append(msg)
            logger.error(msg)

    for prop_name, prop_schema in properties.items():
        if prop_name not in data:
            continue
        value = data[prop_name]

        if "enum" in prop_schema and value not in prop_schema["enum"]:
            msg = (f"{file_label}: Property '{prop_name}' has invalid value "
                   f"'{value}'. Allowed: {prop_schema['enum']}")
            errors.append(msg)
            logger.error(msg)

        if prop_schema.get("type") == "object" and isinstance(value, dict):
            validate_against_schema(
                value, prop_schema, f"{file_label}.{prop_name}", errors, logger
            )

    if schema.get("additionalProperties") is False:
        extra_keys = set(data.keys()) - set(properties.keys())
        for extra in extra_keys:
            msg = f"{file_label}: Unexpected property '{extra}'"
            errors.append(msg)
            logger.error(msg)


def run_module():
    """Main entry point for the Ansible module."""
    module_args = dict(
        input_project_dir=dict(type="str", required=True),
        schema_dir=dict(type="str", required=True),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    input_project_dir = module.params["input_project_dir"]
    schema_dir = module.params["schema_dir"]
    project_name = os.path.basename(input_project_dir)

    logger, log_file = create_logger(project_name)
    logger.info("=== Orchestrator Validation Start ===")

    all_errors = []
    valid_files = []
    invalid_files = []
    loaded_data = {}

    # --- L1: Schema validation for each config file ---
    for vf in VALIDATION_FILES:
        config_path = os.path.join(input_project_dir, vf["config_file"])
        schema_path = os.path.join(schema_dir, vf["schema_file"])

        if not os.path.isfile(config_path):
            if vf["required"]:
                msg = f"Required file not found: {config_path}"
                all_errors.append(msg)
                invalid_files.append(config_path)
                logger.error(msg)
            else:
                logger.info(f"Optional file not found (skipped): {config_path}")
            continue

        if is_vault_encrypted(config_path):
            logger.info(f"Vault-encrypted file (skipped schema check): {config_path}")
            valid_files.append(config_path)
            continue

        data = load_yaml(config_path)
        if data is None:
            msg = f"Failed to parse YAML: {config_path}"
            all_errors.append(msg)
            invalid_files.append(config_path)
            logger.error(msg)
            continue

        schema = load_json(schema_path)
        if schema is None:
            msg = f"Schema file not found: {schema_path}"
            all_errors.append(msg)
            logger.error(msg)
            continue

        file_errors = []
        file_label = os.path.basename(config_path)
        validate_against_schema(data, schema, file_label, file_errors, logger)

        if file_errors:
            all_errors.extend(file_errors)
            invalid_files.append(config_path)
        else:
            valid_files.append(config_path)

        loaded_data[vf["schema_file"]] = data

    # --- L2: Cross-field logic validation ---
    orch_data = loaded_data.get("orchestrator_config.json")
    if orch_data:
        l2_errors = validate_orchestrator_config_l2(orch_data, input_project_dir, logger)
        if l2_errors:
            all_errors.extend(l2_errors)
            logger.error(f"L2 orchestrator_config errors: {l2_errors}")

    ns_data = loaded_data.get("network_spec.json")
    if ns_data:
        ns_errors = []
        validate_network_spec(ns_data, ns_errors, logger)
        if ns_errors:
            all_errors.extend(ns_errors)
            logger.error(f"L2 network_spec errors: {ns_errors}")

    logger.info("=== Orchestrator Validation End ===")

    validation_failed = len(all_errors) > 0
    status = "failed" if validation_failed else "completed"

    message = [
        f"Orchestrator configuration validation {status}.",
        f"Valid files: {len(valid_files)}, Invalid files: {len(invalid_files)}.",
        f"Log file: {log_file}",
    ]

    module.exit_json(
        changed=False,
        validation_failed=validation_failed,
        error_msg=message,
        log_file=log_file,
        errors=all_errors,
        valid_files=valid_files,
        invalid_files=invalid_files,
    )


if __name__ == "__main__":
    run_module()
