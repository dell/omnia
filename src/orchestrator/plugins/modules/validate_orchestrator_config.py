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
"""Validate the complete Orchestrator input contract."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import yaml
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.orchestrator_validation.core.validation_engine import (
    logic as validate_orchestrator_config_l2,
)
from ansible.module_utils.orchestrator_validation.core.validation_engine import (
    logic_additional_cloud_init as validate_additional_cloud_init,
)
from ansible.module_utils.orchestrator_validation.core.validation_engine import (
    logic_network as validate_network_spec,
)
from ansible.module_utils.orchestrator_validation.core.validation_engine import (
    logic_omnia as validate_omnia_config,
)
from ansible.module_utils.orchestrator_validation.core.validation_engine import (
    logic_pxe_mapping as validate_pxe_mapping,
)
from ansible.module_utils.orchestrator_validation.core.validation_engine import (
    logic_security as validate_security_config,
)
from ansible.module_utils.orchestrator_validation.core.validation_engine import (
    logic_storage as validate_storage_config,
)
from ansible.module_utils.orchestrator_validation.core.validation_engine import (
    schema as validate_against_schema,
)
from ansible.module_utils.orchestrator_validation.messages import (
    orchestrator_messages as msg,
)

DOCUMENTATION = r'''
---
module: validate_orchestrator_config
short_description: Validate Orchestrator configuration files
version_added: "2.3.0"
description:
  - Performs complete JSON Schema and cross-field validation.
  - Validates orchestrator_config.yml, omnia_config.yml, network_spec.yml,
    security_config.yml, and storage_config.yml.
  - Validates Kubernetes HA settings on the deployed service_k8s_cluster entry.
  - Validates PXE mapping and additional cloud-init cross-file contracts.
  - Validates storage_config.yml when present and requires it when referenced.
options:
  input_project_dir:
    description: Project input directory containing configuration files.
    required: true
    type: str
  schema_dir:
    description: Directory containing the Orchestrator JSON schemas.
    required: true
    type: str
  log_dir:
    description: Directory where the validation log is written.
    required: false
    type: str
    default: ""
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Validate Orchestrator configuration files
  omnia.orchestrator.validate_orchestrator_config:
    input_project_dir: >-
      {{ orchestrator_data_path }}/input/{{ project_name }}
    schema_dir: >-
      {{ role_path }}/../../plugins/module_utils/orchestrator_validation/schema
    log_dir: "{{ orchestrator_data_path }}/log"
  register: validation_result
'''

RETURN = r'''
validation_failed:
  description: Whether any validation error was found.
  returned: always
  type: bool
errors:
  description: Validation error messages.
  returned: always
  type: list
  elements: str
valid_files:
  description: Files that passed schema and semantic validation.
  returned: always
  type: list
  elements: str
invalid_files:
  description: Files that failed schema or semantic validation.
  returned: always
  type: list
  elements: str
unvalidated_files:
  description: >-
    Vault-encrypted files that could not be decrypted (no sibling
    .<file stem>_key) and therefore were not validated.
  returned: always
  type: list
  elements: str
log_file:
  description: Absolute path to the validation log.
  returned: always
  type: str
error_msg:
  description: Human-readable validation summary lines.
  returned: always
  type: list
  elements: str
'''


VALIDATION_FILES = (
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
    {
        "config_file": "omnia_config.yml",
        "schema_file": "omnia_config.json",
        "required": True,
    },
    {
        "config_file": "storage_config.yml",
        "schema_file": "storage_config.json",
        "required": False,
    },
    {
        "config_file": "security_config.yml",
        "schema_file": "security_config.json",
        "required": True,
    },
)
VAULT_HEADER = "$ANSIBLE_VAULT"


@dataclass
class _ValidationState:
    """Track validation data and structured result collections."""

    errors: list[str] = field(default_factory=list)
    valid_files: list[str] = field(default_factory=list)
    invalid_files: list[str] = field(default_factory=list)
    unvalidated_files: list[str] = field(default_factory=list)
    loaded_data: dict[str, Any] = field(default_factory=dict)
    secrets: list[str] = field(default_factory=list)

    def mark_file(self, path: str, is_valid: bool) -> None:
        """Record file status while preserving any earlier failure."""
        path = os.path.realpath(path)
        if is_valid:
            if path not in self.invalid_files and path not in self.valid_files:
                self.valid_files.append(path)
            return
        if path in self.valid_files:
            self.valid_files.remove(path)
        if path not in self.invalid_files:
            self.invalid_files.append(path)


def create_logger(project_name: str, log_dir: str) -> tuple[logging.Logger, str]:
    """Create a project-specific validation logger.

    Args:
        project_name: Current Omnia project name.
        log_dir: Normalized directory for validation logs.

    Returns:
        Configured logger and absolute log-file path.
    """
    os.makedirs(log_dir, mode=0o750, exist_ok=True)
    log_file = os.path.join(log_dir, f"orchestrator_validation_{project_name}.log")
    logging.basicConfig(
        filename=log_file,
        format="%(asctime)s %(levelname)s %(message)s",
        filemode="w",
        force=True,
    )
    os.chmod(log_file, 0o640)
    logger = logging.getLogger("orchestrator_validation")
    logger.setLevel(logging.DEBUG)
    return logger, log_file


def is_vault_encrypted(path: str) -> bool:
    """Return whether a regular file starts with an Ansible Vault header."""
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as input_file:
            return input_file.readline().strip().startswith(VAULT_HEADER)
    except (OSError, UnicodeError):
        return False


def load_vault_yaml(path: str) -> tuple[Any, str | None, bool]:
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
        return None, msg.yaml_parse_failed_msg(path), True


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


def load_yaml(path: str) -> Any:
    """Load a YAML file, returning None when it cannot be parsed safely."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as yaml_file:
            return yaml.safe_load(yaml_file)
    except (OSError, UnicodeError, yaml.YAMLError):
        return None


def load_json(path: str) -> dict[str, Any] | None:
    """Load a JSON object, returning None when parsing fails."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _validate_file(
    file_config: dict[str, Any],
    input_project_dir: str,
    schema_dir: str,
    state: _ValidationState,
    logger: logging.Logger,
) -> None:
    """Load and schema-validate one configured input file."""
    config_path = os.path.realpath(
        os.path.join(input_project_dir, file_config["config_file"])
    )
    schema_path = os.path.realpath(
        os.path.join(schema_dir, file_config["schema_file"])
    )
    if not os.path.isfile(config_path):
        if file_config["required"]:
            error = msg.required_file_not_found_msg(config_path)
            state.errors.append(error)
            state.mark_file(config_path, False)
            logger.error(error)
        else:
            logger.info(msg.optional_file_skipped_msg(config_path))
        return

    if is_vault_encrypted(config_path):
        data, vault_error, key_available = load_vault_yaml(config_path)
        if not key_available:
            logger.warning(
                "Vault-encrypted file NOT validated (vault key not found): %s",
                config_path,
            )
            state.unvalidated_files.append(config_path)
            return
        if vault_error:
            state.errors.append(vault_error)
            state.mark_file(config_path, False)
            logger.error(vault_error)
            return
        state.secrets = sorted(
            set(state.secrets) | set(collect_secret_strings(data)),
            key=len, reverse=True,
        )
        logger = RedactingLogger(logger, state.secrets)
    else:
        data = load_yaml(config_path)
    if data is None:
        error = msg.yaml_parse_failed_msg(config_path)
        state.errors.append(error)
        state.mark_file(config_path, False)
        logger.error(error)
        return

    schema_definition = load_json(schema_path)
    if schema_definition is None:
        error = msg.schema_file_not_found_msg(schema_path)
        state.errors.append(error)
        state.mark_file(config_path, False)
        logger.error(error)
        return

    file_errors = [
        redact(error, state.secrets)
        for error in validate_against_schema(
            data, schema_definition, os.path.basename(config_path), logger
        )
    ]
    state.errors.extend(file_errors)
    state.mark_file(config_path, not file_errors)
    if not file_errors:
        state.loaded_data[file_config["schema_file"]] = data


def _run_l2_validation(
    input_project_dir: str,
    state: _ValidationState,
    logger: logging.Logger,
) -> None:
    """Run semantic validation and update per-file status."""
    orchestrator_data = state.loaded_data.get("orchestrator_config.json")
    if isinstance(orchestrator_data, dict):
        config_errors = validate_orchestrator_config_l2(
            orchestrator_data, input_project_dir, logger
        )
        if config_errors:
            state.errors.extend(config_errors)
            state.mark_file(
                os.path.join(input_project_dir, "orchestrator_config.yml"),
                False,
            )
            logger.error(
                msg.l2_validation_errors_msg(
                    "orchestrator_config", config_errors
                )
            )

        mapping_errors = validate_pxe_mapping(
            orchestrator_data, input_project_dir, logger
        )
        configured_mapping_path = orchestrator_data.get(
            "pxe_mapping_file_path", ""
        )
        mapping_path = os.path.realpath(
            configured_mapping_path
            or os.path.join(input_project_dir, "pxe_mapping_file.csv")
        )
        state.mark_file(mapping_path, not mapping_errors)
        if mapping_errors:
            state.errors.extend(mapping_errors)
            logger.error(
                msg.l2_validation_errors_msg(
                    "pxe_mapping_file", mapping_errors
                )
            )

        cloud_init_errors = validate_additional_cloud_init(
            orchestrator_data, input_project_dir, logger
        )
        configured_cloud_init_path = orchestrator_data.get(
            "additional_cloud_init_config_file", ""
        )
        if (
            isinstance(configured_cloud_init_path, str)
            and configured_cloud_init_path.strip()
        ):
            cloud_init_path = os.path.realpath(
                configured_cloud_init_path.strip()
            )
            state.mark_file(cloud_init_path, not cloud_init_errors)
        if cloud_init_errors:
            state.errors.extend(cloud_init_errors)
            logger.error(
                msg.l2_validation_errors_msg(
                    "additional_cloud_init", cloud_init_errors
                )
            )

    network_data = state.loaded_data.get("network_spec.json")
    if isinstance(network_data, dict):
        errors = validate_network_spec(network_data, logger)
        if errors:
            state.errors.extend(errors)
            state.mark_file(
                os.path.join(input_project_dir, "network_spec.yml"), False
            )
            logger.error(msg.l2_validation_errors_msg("network_spec", errors))

    security_data = state.loaded_data.get("security_config.json")
    if isinstance(security_data, dict):
        errors = validate_security_config(security_data, logger)
        if errors:
            state.errors.extend(errors)
            state.mark_file(
                os.path.join(input_project_dir, "security_config.yml"), False
            )
            logger.error(
                msg.l2_validation_errors_msg("security_config", errors)
            )

    omnia_data = state.loaded_data.get("omnia_config.json")
    storage_data = state.loaded_data.get("storage_config.json")
    if isinstance(storage_data, dict):
        errors = validate_storage_config(
            storage_data,
            orchestrator_data if isinstance(orchestrator_data, dict) else {},
            omnia_data if isinstance(omnia_data, dict) else {},
            input_project_dir,
            logger,
        )
        if errors:
            state.errors.extend(errors)
            state.mark_file(
                os.path.join(input_project_dir, "storage_config.yml"), False
            )
            logger.error(
                msg.l2_validation_errors_msg("storage_config", errors)
            )

    if isinstance(omnia_data, dict):
        auxiliary_file_statuses: dict[str, bool] = {}
        auxiliary_errors: list[str] = []
        errors = validate_omnia_config(
            omnia_data,
            input_project_dir,
            logger,
            auxiliary_file_statuses,
            auxiliary_errors,
        )
        for path, is_valid in auxiliary_file_statuses.items():
            state.mark_file(path, is_valid)
        state.errors.extend(errors)
        remaining_auxiliary_errors = Counter(auxiliary_errors)
        intrinsic_errors = []
        for error in errors:
            if remaining_auxiliary_errors[error]:
                remaining_auxiliary_errors[error] -= 1
            else:
                intrinsic_errors.append(error)
        if intrinsic_errors:
            state.mark_file(
                os.path.join(input_project_dir, "omnia_config.yml"), False
            )
            logger.error(
                msg.l2_validation_errors_msg(
                    "omnia_config", intrinsic_errors
                )
            )
        if auxiliary_errors:
            logger.error(
                msg.l2_validation_errors_msg(
                    "omnia_config auxiliary inputs", auxiliary_errors
                )
            )


def run_module() -> None:
    """Run the Ansible module and return structured validation results."""
    module = AnsibleModule(
        argument_spec={
            "input_project_dir": {"type": "str", "required": True},
            "schema_dir": {"type": "str", "required": True},
            "log_dir": {"type": "str", "required": False, "default": ""},
        },
        supports_check_mode=True,
    )
    input_project_dir = os.path.realpath(module.params["input_project_dir"])
    schema_dir = os.path.realpath(module.params["schema_dir"])
    orchestrator_data_path = os.getenv("ORCHESTRATOR_DATA_PATH") or os.path.join(
        os.getenv("OMNIA_DATA_PATH") or "/opt/omnia", "orchestrator"
    )
    configured_log_dir = module.params["log_dir"] or os.path.join(
        orchestrator_data_path, "log"
    )
    log_dir = os.path.realpath(configured_log_dir)
    project_name = os.path.basename(input_project_dir)
    logger, log_file = create_logger(project_name, log_dir)
    logger.info(msg.VALIDATION_START_MSG)

    state = _ValidationState()
    for file_config in VALIDATION_FILES:
        _validate_file(
            file_config, input_project_dir, schema_dir, state, logger
        )
    _run_l2_validation(
        input_project_dir,
        state,
        RedactingLogger(logger, state.secrets) if state.secrets else logger,
    )
    state.errors = [redact(error, state.secrets) for error in state.errors]
    logger.info(msg.VALIDATION_END_MSG)

    validation_failed = bool(state.errors) or bool(state.unvalidated_files)
    status = "failed" if validation_failed else "completed"
    summary = [
        msg.validation_status_msg(status),
        msg.validation_counts_msg(
            len(state.valid_files), len(state.invalid_files)
        ),
        f"Not validated (encrypted, no vault key): {len(state.unvalidated_files)}.",
        msg.validation_log_msg(log_file),
    ]
    module.exit_json(
        changed=False,
        validation_failed=validation_failed,
        error_msg=summary,
        log_file=log_file,
        errors=state.errors,
        valid_files=state.valid_files,
        invalid_files=state.invalid_files,
        unvalidated_files=state.unvalidated_files,
    )


def main() -> None:
    """Run the module entry point."""
    run_module()


if __name__ == "__main__":
    main()
