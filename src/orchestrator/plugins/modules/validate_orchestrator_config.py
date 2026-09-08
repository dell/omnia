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
from dataclasses import dataclass, field
from typing import Any

import yaml
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.orchestrator_validation.core.validation_engine import (
    logic as validate_orchestrator_config_l2,
    logic_network as validate_network_spec,
    logic_storage as validate_storage_references,
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
  - Validates orchestrator_config.yml and network_spec.yml.
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
      {{ omnia_data_path }}/orchestrator/input/{{ project_name }}
    schema_dir: >-
      {{ role_path }}/../../plugins/module_utils/orchestrator_validation/schema
    log_dir: "{{ omnia_data_path }}/log/core/playbooks"
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
        "config_file": "storage_config.yml",
        "schema_file": "storage_config.json",
        "required": False,
    },
)
VAULT_HEADER = "$ANSIBLE_VAULT"


@dataclass
class _ValidationState:
    """Track validation data and structured result collections."""

    errors: list[str] = field(default_factory=list)
    valid_files: list[str] = field(default_factory=list)
    invalid_files: list[str] = field(default_factory=list)
    loaded_data: dict[str, Any] = field(default_factory=dict)

    def mark_file(self, path: str, is_valid: bool) -> None:
        """Record a path once in the appropriate result collection."""
        target = self.valid_files if is_valid else self.invalid_files
        other = self.invalid_files if is_valid else self.valid_files
        if path in other:
            other.remove(path)
        if path not in target:
            target.append(path)


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
        logger.info(msg.vault_file_skipped_msg(config_path))
        state.mark_file(config_path, True)
        return

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

    file_errors = validate_against_schema(
        data, schema_definition, os.path.basename(config_path), logger
    )
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
        errors = validate_orchestrator_config_l2(
            orchestrator_data, input_project_dir, logger
        )
        if errors:
            state.errors.extend(errors)
            state.mark_file(
                os.path.join(input_project_dir, "orchestrator_config.yml"), False
            )
            logger.error(msg.l2_validation_errors_msg("orchestrator_config", errors))

    network_data = state.loaded_data.get("network_spec.json")
    if isinstance(network_data, dict):
        errors = validate_network_spec(network_data, logger)
        if errors:
            state.errors.extend(errors)
            state.mark_file(
                os.path.join(input_project_dir, "network_spec.yml"), False
            )
            logger.error(msg.l2_validation_errors_msg("network_spec", errors))

    storage_errors = validate_storage_references(
        input_project_dir,
        state.loaded_data.get("storage_config.json"),
        logger,
    )
    if storage_errors:
        state.errors.extend(storage_errors)
        state.mark_file(
            os.path.join(input_project_dir, "storage_config.yml"), False
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
    configured_log_dir = module.params["log_dir"] or os.path.join(
        os.getenv("OMNIA_DATA_PATH", "/opt/omnia"), "log", "core", "playbooks"
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
    _run_l2_validation(input_project_dir, state, logger)
    logger.info(msg.VALIDATION_END_MSG)

    validation_failed = bool(state.errors)
    status = "failed" if validation_failed else "completed"
    summary = [
        msg.validation_status_msg(status),
        msg.validation_counts_msg(
            len(state.valid_files), len(state.invalid_files)
        ),
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
    )


def main() -> None:
    """Run the module entry point."""
    run_module()


if __name__ == "__main__":
    main()
