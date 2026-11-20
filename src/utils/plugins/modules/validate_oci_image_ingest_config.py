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
# ****
# Secure code generated utilizing Code Guardian.
# Applicable rules used: CG-CONFIG-001.5, CG-CRYPTO-001.6
# ****

"""Validate oci_image_ingest_config.yml (JSON Schema plus semantic checks)."""

from __future__ import annotations

import json
import os

import yaml
from ansible.module_utils.basic import AnsibleModule

try:
    from ansible.module_utils.input_validation.core.utils import create_logger
    from ansible.module_utils.input_validation.core.validation_engine import (
        credential_keys_oci_image_ingest_config,
        format_oci_image_ingest_config_error,
        logic_oci_image_ingest_config,
        schema as validate_against_schema,
    )
    HAS_ENGINE = True
except ImportError:  # jsonschema or the validation package is unavailable
    HAS_ENGINE = False

DOCUMENTATION = r"""
---
module: validate_oci_image_ingest_config
short_description: Validate oci_image_ingest_config.yml
version_added: "2.3.0"
description:
  - Runs L1 (JSON Schema) and L2 (business logic) validation through the utils input validation engine.
  - Rejects credential keys without echoing their values.
  - Returns the configuration with the default registry port applied.
options:
  config_path:
    description: Path to oci_image_ingest_config.yml.
    type: path
    required: true
  schema_path:
    description: Path to oci_image_ingest_config.json.
    type: path
    required: true
  log_dir:
    description: Directory for the utils log file; no log is written when empty.
    type: path
    default: ""
author:
  - Dell Omnia Team
"""

EXAMPLES = r"""
- name: Validate the OCI image ingest configuration
  validate_oci_image_ingest_config:
    config_path: /opt/omnia/utils/input/project_default/oci_image_ingest_config.yml
    schema_path: "{{ role_path }}/../../plugins/module_utils/input_validation/schema/oci_image_ingest_config.json"
"""

RETURN = r"""
config:
  description: Normalized registries and image_mappings.
  returned: success
  type: dict
errors:
  description: Validation errors.
  returned: failure
  type: list
  elements: str
"""

LOG_NAME = "oci_image_ingest"
DEFAULT_PORTS = {"https": 443, "http": 80}
FILE_LABEL = "oci_image_ingest_config"


def validate_config(config, schema_def, logger):
    """Return the list of L1 and L2 errors for a parsed configuration."""
    if not isinstance(config, dict):
        return ["oci_image_ingest_config.yml must be a YAML mapping with registries "
                "and image_mappings"]
    cred_errors = credential_keys_oci_image_ingest_config(config)
    if cred_errors:
        return cred_errors
    errors = []
    validate_against_schema(config, schema_def, FILE_LABEL, errors, logger,
                            formatter=format_oci_image_ingest_config_error)
    if errors:
        return errors
    return logic_oci_image_ingest_config(config, logger)


def normalize(config):
    """Apply the default registry port."""
    registries = []
    for reg in config["registries"]:
        reg = dict(reg)
        reg.setdefault("registry_port", DEFAULT_PORTS[reg["registry_protocol"]])
        registries.append(reg)
    return {"registries": registries, "image_mappings": config["image_mappings"]}


def main() -> None:
    """Module entry point."""
    module = AnsibleModule(
        argument_spec={"config_path": {"type": "path", "required": True},
                       "schema_path": {"type": "path", "required": True},
                       "log_dir": {"type": "path", "default": ""}},
        supports_check_mode=True,
    )
    if not HAS_ENGINE:
        module.fail_json(msg="python jsonschema library and the utils input validation "
                             "package are required")
    for key in ("config_path", "schema_path"):
        if not os.path.isfile(module.params[key]):
            module.fail_json(msg=f"{key} not found: {module.params[key]}")
    try:
        with open(module.params["config_path"], encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
        with open(module.params["schema_path"], encoding="utf-8") as handle:
            schema_def = json.load(handle)
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        module.fail_json(msg=f"Failed to parse input: {type(exc).__name__}")
    logger = create_logger(module.params["log_dir"], LOG_NAME)
    errors = validate_config(config, schema_def, logger)
    if errors:
        module.fail_json(msg="oci_image_ingest_config.yml validation failed", errors=errors)
    logger.info("oci_image_ingest_config.yml validated")
    module.exit_json(changed=False, msg="oci_image_ingest_config.yml is valid",
                     config=normalize(config))


if __name__ == "__main__":
    main()
