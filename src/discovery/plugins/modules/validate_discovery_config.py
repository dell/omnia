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
Ansible module for discovery-specific input validation.

Performs L1 (JSON schema) and L2 (cross-field logic) validation on:
  - discovery_config.yml (required)
  - network_spec.yml (required)

Usage in a playbook:
  - name: Validate discovery configuration
    validate_discovery_config:
      input_project_dir: "{{ input_project_dir }}"
      schema_dir: "{{ role_path }}/../../../plugins/module_utils/discovery_validation/schema"
"""

import json
import logging
import os
import re
import subprocess
from typing import Any, Optional, Tuple

import yaml
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.discovery_validation.discovery_validation_flow import (
    validate_discovery_config,
)


DOCUMENTATION = r'''
---
module: validate_discovery_config
short_description: Validate discovery configuration files
description:
  - Performs L1 (JSON schema) and L2 (cross-field logic) validation on discovery_config.yml.
options:
  input_project_dir:
    description: Path to the input project directory containing configuration files.
    required: true
    type: str
  schema_dir:
    description: Path to the directory containing JSON schema files.
    required: true
    type: str
  log_dir:
    description: Directory where the validation log is written.
    required: false
    type: str
'''

EXAMPLES = r'''
- name: Validate discovery configuration files
  validate_discovery_config:
    input_project_dir: "{{ discovery_data_path }}/input/{{ discovery_project_name }}"
    schema_dir: "{{ role_path }}/../../plugins/module_utils/discovery_validation/schema"
    log_dir: "{{ discovery_data_path }}/log/{{ discovery_project_name }}"
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
unvalidated_files:
  description: >-
    Vault-encrypted files that could not be decrypted (no sibling
    .<file stem>_key) and therefore were not validated.
  type: list
  returned: always
'''

VALIDATION_LOG_PATH = os.path.join(
    os.environ.get("DISCOVERY_DATA_PATH")
    or os.path.join(os.environ.get("OMNIA_DATA_PATH", "/opt/omnia"), "discovery"),
    "log",
)

# Files to validate and their corresponding schema names
VALIDATION_FILES = [
    {
        "config_file": "discovery_config.yml",
        "schema_file": "discovery_config.json",
        "required": True,
    },
    {
        "config_file": "network_spec.yml",
        "schema_file": "network_spec.json",
        "required": True,
    },
]


def create_logger(
    project_name: str, log_dir: str = VALIDATION_LOG_PATH
) -> Tuple[logging.Logger, str]:
    """Create a logger for discovery validation."""
    log_file = os.path.join(
        log_dir, f"discovery_validation_{project_name}.log"
    )
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logging.basicConfig(
        filename=log_file,
        format="%(asctime)s %(levelname)s %(message)s",
        filemode="w",
    )
    logger = logging.getLogger("discovery_validation")
    logger.setLevel(logging.DEBUG)
    return logger, log_file


VAULT_HEADER = "$ANSIBLE_VAULT"


def is_vault_encrypted(path: str) -> bool:
    """Check if a file is Ansible Vault encrypted."""
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
    return first_line.startswith(VAULT_HEADER)


def load_vault_yaml(path: str) -> Tuple[Any, Optional[str], bool]:
    """Decrypt a vault file in memory with its sibling ``.<stem>_key`` file.

    Returns:
        (data, error, key_available). key_available is False when no vault key
        exists, in which case the file cannot be validated.
    """
    stem = os.path.splitext(os.path.basename(path))[0]
    key_path = os.path.join(os.path.dirname(path), f".{stem}_key")
    if not os.path.isfile(key_path):
        return None, None, False
    try:
        result = subprocess.run(
            ["ansible-vault", "view", path, "--vault-password-file", key_path],
            capture_output=True, text=True, check=False, timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"Unable to decrypt vault file {path}: {exc}", True
    if result.returncode != 0:
        return None, f"Unable to decrypt vault file {path}: {result.stderr.strip()}", True
    try:
        return yaml.safe_load(result.stdout), None, True
    except yaml.YAMLError:
        return None, f"Failed to parse decrypted YAML: {path}", True


REDACTED = "********"


def collect_secret_strings(data: Any) -> list[str]:
    """Return every scalar value (not key) in decrypted data, longest first."""
    found, stack = set(), [data]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
        elif isinstance(item, str) and item:
            found.add(item)
        elif isinstance(item, (int, float)) and not isinstance(item, bool):
            found.add(str(item))
    return sorted(found, key=len, reverse=True)


def redact(text: Any, secrets: list[str]) -> str:
    """Mask decrypted secret values (quoted always, bare when 3+ chars)."""
    text = str(text)
    for secret in secrets:
        text = text.replace(repr(secret), REDACTED)
        if len(secret) >= 3:
            text = text.replace(secret, REDACTED)
    return text


class RedactingLogger(logging.LoggerAdapter):
    """Logger adapter that masks decrypted secret values in log messages."""

    def __init__(self, logger: logging.Logger, secrets: list[str]):
        super().__init__(logger, {})
        self.secrets = secrets

    def process(self, msg, kwargs):
        return redact(msg, self.secrets), kwargs


def load_yaml(path: str) -> Optional[dict[str, Any]]:
    """Load a YAML file, returning None on failure."""
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path: str) -> Optional[dict[str, Any]]:
    """Load a JSON file, returning None on failure."""
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_against_schema(
    data: Any,
    schema: dict[str, Any],
    file_label: str,
    errors: list[str],
    logger: logging.Logger
) -> None:
    """
    Validate data against a JSON schema (L1).
    Enforces required, type, enum, and string constraints without a jsonschema
    dependency. Fails closed on an empty schema and matches string patterns
    against the whole value.
    """
    if not schema:
        msg = f"{file_label}: Schema is empty; refusing to treat input as valid"
        errors.append(msg)
        logger.error(msg)
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

        expected_type = prop_schema.get("type")
        type_matches = {
            "string": isinstance(value, str),
            "boolean": isinstance(value, bool),
            "object": isinstance(value, dict),
            "array": isinstance(value, list),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "number": isinstance(value, (int, float))
            and not isinstance(value, bool),
        }.get(expected_type, True)
        if not type_matches:
            msg = (
                f"{file_label}: Property '{prop_name}' must be of type "
                f"'{expected_type}'"
            )
            errors.append(msg)
            logger.error(msg)
            continue

        if "enum" in prop_schema and value not in prop_schema["enum"]:
            msg = (f"{file_label}: Property '{prop_name}' has invalid value "
                   f"'{value}'. Allowed: {prop_schema['enum']}")
            errors.append(msg)
            logger.error(msg)

        if isinstance(value, str):
            invalid_length = (
                len(value) < prop_schema.get("minLength", 0)
                or (
                    "maxLength" in prop_schema
                    and len(value) > prop_schema["maxLength"]
                )
            )
            invalid_pattern = (
                "pattern" in prop_schema
                and re.fullmatch(prop_schema["pattern"], value) is None
            )
            if invalid_length or invalid_pattern:
                msg = prop_schema.get(
                    "errorMessage",
                    f"{file_label}: Property '{prop_name}' has an invalid value",
                )
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


def run_module() -> None:
    """Main entry point for the Ansible module."""
    module_args = {
        "input_project_dir": {"type": "str", "required": True},
        "schema_dir": {"type": "str", "required": True},
        "log_dir": {"type": "str", "required": False, "default": ""},
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    input_project_dir = module.params["input_project_dir"]
    schema_dir = module.params["schema_dir"]
    log_dir = module.params["log_dir"] or VALIDATION_LOG_PATH
    project_name = os.path.basename(input_project_dir)

    logger, log_file = create_logger(project_name, log_dir)
    logger.info("=== Discovery Validation Start ===")

    all_errors = []
    valid_files = []
    invalid_files = []
    unvalidated_files = []

    # --- L1: Schema validation for each config file ---
    config_data = None
    for vf in VALIDATION_FILES:
        config_path = os.path.join(input_project_dir, vf["config_file"])
        schema_path = os.path.join(schema_dir, vf["schema_file"])
        secrets: list[str] = []

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
            secrets = collect_secret_strings(data)
        else:
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
            invalid_files.append(config_path)
            logger.error(msg)
            continue

        file_errors = []
        file_label = os.path.basename(config_path)
        file_logger = RedactingLogger(logger, secrets) if secrets else logger
        validate_against_schema(data, schema, file_label, file_errors, file_logger)
        file_errors = [redact(err, secrets) for err in file_errors]

        if file_errors:
            all_errors.extend(file_errors)
            invalid_files.append(config_path)
        else:
            valid_files.append(config_path)

        if vf["schema_file"] == "discovery_config.json":
            config_data = data

    # --- L2: Cross-field logic validation ---
    if isinstance(config_data, dict):
        l2_errors = validate_discovery_config(config_data, logger)
        if l2_errors:
            all_errors.extend(l2_errors)
            logger.error(f"L2 validation errors: {l2_errors}")

    logger.info("=== Discovery Validation End ===")

    validation_failed = len(all_errors) > 0 or len(unvalidated_files) > 0
    status = "failed" if validation_failed else "completed"

    message = [
        f"Discovery configuration validation {status}.",
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


if __name__ == "__main__":
    run_module()
