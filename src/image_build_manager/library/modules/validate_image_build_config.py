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
Ansible module for image_build_manager-specific input validation.

Performs L1 (JSON schema) and L2 (cross-field logic) validation on:
  - image_build_config.yml
  - image_build_credentials.yml (if exists and decrypted)
  - functional_groups_config.yml (if exists)

Usage in a playbook:
  - name: Validate image build configuration
    validate_image_build_config:
      input_project_dir: "{{ input_project_dir }}"
      schema_dir: "{{ role_path }}/../../../library/module_utils/image_build_validation/schema"
"""

import json
import logging
import os

import yaml
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.image_build_validation.image_build_validation_flow import (
    validate_image_build_config,
    validate_credentials_logic,
)


VALIDATION_LOG_PATH = "/opt/omnia/log/core/playbooks/"

# Files to validate and their corresponding schema names
VALIDATION_FILES = [
    {
        "config_file": "image_build_manager/image_build_config.yml",
        "schema_file": "image_build_config.json",
        "required": True,
    },
    {
        "config_file": "image_build_manager/image_build_credentials.yml",
        "schema_file": "image_build_credentials.json",
        "required": False,
    },
]


def create_logger(project_name):
    """Create a logger for image_build validation."""
    log_file = os.path.join(
        VALIDATION_LOG_PATH, f"image_build_validation_{project_name}.log"
    )
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logging.basicConfig(
        filename=log_file,
        format="%(asctime)s %(levelname)s %(message)s",
        filemode="w",
    )
    logger = logging.getLogger("image_build_validation")
    logger.setLevel(logging.DEBUG)
    return logger, log_file


# Ansible Vault header prefix
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

    # Check required properties
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    for req_key in required:
        if req_key not in data:
            msg = f"{file_label}: Missing required property '{req_key}'"
            errors.append(msg)
            logger.error(msg)

    # Check enum constraints
    for prop_name, prop_schema in properties.items():
        if prop_name not in data:
            continue
        value = data[prop_name]

        if "enum" in prop_schema and value not in prop_schema["enum"]:
            msg = (f"{file_label}: Property '{prop_name}' has invalid value "
                   f"'{value}'. Allowed: {prop_schema['enum']}")
            errors.append(msg)
            logger.error(msg)

        # Recurse into nested objects
        if prop_schema.get("type") == "object" and isinstance(value, dict):
            validate_against_schema(
                value, prop_schema, f"{file_label}.{prop_name}", errors, logger
            )

    # Check additionalProperties constraint
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
    logger.info("=== Image Build Manager Validation Start ===")

    all_errors = []
    valid_files = []
    invalid_files = []

    # --- L1: Schema validation for each config file ---
    config_data = None
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

        # Skip Ansible Vault encrypted files — they cannot be validated
        # without the vault password (handled by Ansible at runtime)
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

        # Keep config data for L2 validation
        if vf["schema_file"] == "image_build_config.json":
            config_data = data

    # --- L2: Cross-field logic validation ---
    if config_data:
        l2_errors = validate_image_build_config(config_data, logger)
        if l2_errors:
            all_errors.extend(l2_errors)
            logger.error(f"L2 validation errors: {l2_errors}")

        # Cross-validate credentials against config if both exist and decrypted
        cred_path = os.path.join(
            input_project_dir, "image_build_manager/image_build_credentials.yml"
        )
        if os.path.isfile(cred_path) and not is_vault_encrypted(cred_path):
            cred_data = load_yaml(cred_path)
            if cred_data and isinstance(cred_data, dict):
                cred_errors = []
                validate_credentials_logic(
                    cred_data, config_data, cred_errors, logger
                )
                if cred_errors:
                    all_errors.extend(cred_errors)
            elif cred_data and not isinstance(cred_data, dict):
                logger.warning(
                    f"Credential file is not a dict (possibly vault-encrypted): {cred_path}"
                )

    logger.info("=== Image Build Manager Validation End ===")

    validation_failed = len(all_errors) > 0
    status = "failed" if validation_failed else "completed"

    message = [
        f"Image build configuration validation {status}.",
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


def main():
    """Main entry point."""
    run_module()


if __name__ == "__main__":
    main()
