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
  - package_groups.yml (required in config mode; validated when present)
  - catalog JSON selected by CATALOG_FILE_PATH (required in catalog mode)

Usage in a playbook:
  - name: Validate image build configuration
    validate_image_build_config:
      input_project_dir: "{{ input_project_dir }}"
      schema_dir: "{{ role_path }}/../../../plugins/module_utils/input_validation/schema"
"""

import os

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.input_validation.core.config import (
    VALIDATION_FILES,
)
from ansible.module_utils.input_validation.core.file_utils import (
    RedactingLogger,
    collect_secret_strings,
    is_vault_encrypted,
    load_json,
    load_vault_yaml,
    load_yaml,
    redact,
    split_placeholders,
)
from ansible.module_utils.input_validation.core.utils import create_logger
from ansible.module_utils.input_validation.core.validation_engine import (
    logic as validate_image_build_config,
    logic_catalog as validate_catalog_logic,
    logic_credentials as validate_credentials_logic_new,
    schema as validate_against_schema,
)
from ansible.module_utils.input_validation.messages import (
    image_build_messages as msg,
)

DOCUMENTATION = r'''
---
module: validate_image_build_config
short_description: Validate image build configuration files
version_added: "2.3.0"
description:
  - Performs L1 (JSON schema) validation on image_build_config.yml and
    image_build_credentials.yml, package_groups.yml, and catalog JSON.
  - Performs L2 (cross-field logic) validation on config values.
  - Decrypts Ansible Vault encrypted files in memory using the sibling
    C(.<file stem>_key) vault key. Encrypted files without a key are reported
    in C(unvalidated_files) and never counted as valid.
  - Returns structured validation results with error details and log path.
options:
  input_project_dir:
    description: Path to the project input directory containing config files.
    required: true
    type: str
  schema_dir:
    description: Path to the directory containing JSON schema files.
    required: true
    type: str
  log_dir:
    description: Override default log directory for validation logs.
    required: false
    type: str
    default: ""
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Validate image build configuration
  omnia.image_build.validate_image_build_config:
    input_project_dir: /opt/omnia/image_build_manager/input/project_default
    schema_dir: "{{ role_path }}/../../../plugins/module_utils/input_validation/schema"
  register: validation

- name: Fail if validation errors found
  ansible.builtin.fail:
    msg: "{{ validation.errors | join('; ') }}"
  when: validation.validation_failed
'''

RETURN = r'''
validation_failed:
  description: Whether any validation errors were found.
  returned: always
  type: bool
errors:
  description: List of validation error messages.
  returned: always
  type: list
  elements: str
valid_files:
  description: List of files that passed validation.
  returned: always
  type: list
  elements: str
invalid_files:
  description: List of files that failed validation.
  returned: always
  type: list
  elements: str
unvalidated_files:
  description: Vault-encrypted files that could not be decrypted for validation.
  returned: always
  type: list
  elements: str
log_file:
  description: Path to the validation log file.
  returned: always
  type: str
'''


VALIDATION_LOG_PATH = os.path.join(
    os.environ.get("OMNIA_DATA_PATH", "/opt/omnia"),
    "image_build_manager", "log"
)  # Derived from OMNIA_DATA_PATH — overridden by log_dir param


def _validate_document(data, schema_path, file_label, errors, logger, placeholders=()):
    """Validate a document against its complete JSON Schema contract.

    Keys in ``placeholders`` are credential values not collected yet; they are
    not required here because the credential prompt runs after validation.
    """
    schema_def = load_json(schema_path)
    if schema_def is None:
        error = msg.schema_file_not_found_msg(schema_path)
        errors.append(error)
        logger.error(error)
        return False
    if placeholders:
        schema_def = dict(schema_def, required=[
            key for key in schema_def.get("required", []) if key not in placeholders
        ])

    initial_error_count = len(errors)
    validate_against_schema(data, schema_def, file_label, errors, logger)
    return len(errors) == initial_error_count


def _mark_file(path, is_valid, valid_files, invalid_files):
    """Record a path once in the appropriate validation result list."""
    target = valid_files if is_valid else invalid_files
    other = invalid_files if is_valid else valid_files
    if path in other:
        other.remove(path)
    if path not in target:
        target.append(path)


def _validate_catalog(schema_dir, errors, valid_files, invalid_files, logger):
    """Validate the catalog selected through CATALOG_FILE_PATH."""
    catalog_file = os.environ.get("CATALOG_FILE_PATH", "")
    if not catalog_file:
        errors.append(msg.CATALOG_PATH_REQUIRED_MSG)
        logger.error(msg.CATALOG_PATH_REQUIRED_MSG)
        return

    if not os.path.isfile(catalog_file):
        errors.append(msg.CATALOG_FILE_NOT_FOUND_MSG)
        _mark_file(catalog_file, False, valid_files, invalid_files)
        logger.error(msg.CATALOG_FILE_NOT_FOUND_MSG)
        return

    catalog_data = load_json(catalog_file)
    if catalog_data is None:
        error = f"Failed to parse JSON: {catalog_file}"
        errors.append(error)
        _mark_file(catalog_file, False, valid_files, invalid_files)
        logger.error(error)
        return

    catalog_errors = []
    schema_valid = _validate_document(
        catalog_data,
        os.path.join(schema_dir, "catalog.json"),
        os.path.basename(catalog_file),
        catalog_errors,
        logger,
    )
    if schema_valid:
        catalog_errors.extend(validate_catalog_logic(catalog_file, logger))
    errors.extend(catalog_errors)
    _mark_file(
        catalog_file,
        not catalog_errors,
        valid_files,
        invalid_files,
    )


def _validate_package_groups(
    input_project_dir,
    schema_dir,
    required,
    errors,
    valid_files,
    invalid_files,
    logger,
):
    """Validate package_groups.yml when present or required by config mode."""
    package_groups_path = os.path.join(input_project_dir, "package_groups.yml")
    if not os.path.isfile(package_groups_path):
        if required:
            errors.append(msg.PACKAGE_GROUPS_REQUIRED_MSG)
            _mark_file(package_groups_path, False, valid_files, invalid_files)
            logger.error(msg.PACKAGE_GROUPS_REQUIRED_MSG)
        return

    package_groups_data = load_yaml(package_groups_path)
    package_errors = []
    if package_groups_data is None:
        package_errors.append(msg.yaml_parse_failed_msg(package_groups_path))
    else:
        _validate_document(
            package_groups_data,
            os.path.join(schema_dir, "package_groups.json"),
            "package_groups.yml",
            package_errors,
            logger,
        )
    errors.extend(package_errors)
    _mark_file(
        package_groups_path,
        not package_errors,
        valid_files,
        invalid_files,
    )


def run_module():
    """Main entry point for the Ansible module."""
    module_args = dict(
        input_project_dir=dict(type="str", required=True),
        schema_dir=dict(type="str", required=True),
        log_dir=dict(type="str", required=False, default=""),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    input_project_dir = module.params["input_project_dir"]
    schema_dir = module.params["schema_dir"]
    log_dir = module.params.get("log_dir", "")
    project_name = os.path.basename(input_project_dir)

    # Use provided log_dir or fall back to default
    log_path = log_dir if log_dir else VALIDATION_LOG_PATH
    logger, log_file = create_logger(log_path, project_name)
    logger.info(msg.VALIDATION_START_MSG)

    all_errors = []
    valid_files = []
    invalid_files = []
    unvalidated_files = []
    loaded_data = {}
    secrets_by_file = {}
    placeholders_by_file = {}

    # --- L1: Schema validation for each config file ---
    config_data = None
    for vf in VALIDATION_FILES:
        config_path = os.path.join(input_project_dir, vf["config_file"])
        schema_path = os.path.join(schema_dir, vf["schema_file"])

        if not os.path.isfile(config_path):
            if vf["required"]:
                err = msg.required_file_not_found_msg(config_path)
                all_errors.append(err)
                invalid_files.append(config_path)
                logger.error(err)
            else:
                logger.info(f"Optional file not found (skipped): {config_path}")
            continue

        # Vault-encrypted files are decrypted in memory and validated like any
        # other file. Without a vault key they are reported as not validated.
        if is_vault_encrypted(config_path):
            data, vault_error, key_available = load_vault_yaml(config_path)
            if not key_available:
                logger.warning(
                    f"Vault-encrypted file NOT validated (vault key not found): {config_path}"
                )
                unvalidated_files.append(config_path)
                continue
            if vault_error:
                all_errors.append(vault_error)
                invalid_files.append(config_path)
                logger.error(vault_error)
                continue
            secrets_by_file[vf["config_file"]] = collect_secret_strings(data)
            data, placeholders = split_placeholders(data)
            if placeholders:
                placeholders_by_file[vf["config_file"]] = placeholders
                logger.info(
                    f"Not yet collected (validated after the credential prompt): "
                    f"{sorted(placeholders)} in {config_path}"
                )
        else:
            data = load_yaml(config_path)
        if data is None:
            err = msg.yaml_parse_failed_msg(config_path)
            all_errors.append(err)
            invalid_files.append(config_path)
            logger.error(err)
            continue

        loaded_data[vf["config_file"]] = data
        secrets = secrets_by_file.get(vf["config_file"], [])
        file_label = os.path.basename(config_path)
        file_errors = []
        is_valid = _validate_document(
            data, schema_path, file_label, file_errors,
            RedactingLogger(logger, secrets) if secrets else logger,
            placeholders_by_file.get(vf["config_file"], ()),
        )
        file_errors = [redact(err, secrets) for err in file_errors]
        all_errors.extend(file_errors)
        _mark_file(config_path, is_valid, valid_files, invalid_files)

        # Keep config data for L2 validation
        if vf["schema_file"] == "image_build_config.json":
            # L2 validators assume the schema-established types. Do not pass
            # malformed values (for example quoted booleans) into them.
            config_data = data if is_valid else None

    # --- L2: Cross-field logic validation ---
    if config_data:
        l2_errors = validate_image_build_config(config_data, logger)
        if l2_errors:
            all_errors.extend(l2_errors)
            logger.error(f"L2 validation errors: {l2_errors}")

        # Catalog validation (when functional_groups_source == 'catalog')
        fg_source = config_data.get("functional_groups_source", "config")
        if fg_source == "catalog":
            _validate_catalog(
                schema_dir,
                all_errors,
                valid_files,
                invalid_files,
                logger,
            )

        # package_groups.yml is required in config mode and schema-validated
        # whenever it is supplied, including catalog mode.
        _validate_package_groups(
            input_project_dir,
            schema_dir,
            fg_source == "config",
            all_errors,
            valid_files,
            invalid_files,
            logger,
        )

        # Cross-validate credentials (plaintext or decrypted vault) against config
        cred_data = loaded_data.get("image_build_credentials.yml")
        if "image_build_credentials.yml" in placeholders_by_file:
            logger.info("Credential logic check deferred: credentials not yet collected.")
        elif cred_data and isinstance(cred_data, dict):
            secrets = secrets_by_file.get("image_build_credentials.yml", [])
            cred_errors = validate_credentials_logic_new(
                cred_data, config_data,
                RedactingLogger(logger, secrets) if secrets else logger,
            )
            if cred_errors:
                all_errors.extend(redact(err, secrets) for err in cred_errors)
        elif cred_data:
            logger.warning("Credential file is not a mapping: image_build_credentials.yml")

    logger.info(msg.VALIDATION_END_MSG)

    validation_failed = len(all_errors) > 0 or len(unvalidated_files) > 0
    status = "failed" if validation_failed else "completed"

    message = [
        f"Image build configuration validation {status}.",
        f"Valid files: {len(valid_files)}, Invalid files: {len(invalid_files)}, "
        f"Not validated (encrypted, no vault key): {len(unvalidated_files)}.",
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
        unvalidated_files=unvalidated_files,
    )


def main():
    """Main entry point."""
    run_module()


if __name__ == "__main__":
    main()
