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

"""Validate the decrypted oci_image_ingest credentials without echoing their values."""

from __future__ import annotations

import json
import os

from ansible.module_utils.basic import AnsibleModule

try:
    from ansible.module_utils.input_validation.core.utils import create_logger
    from ansible.module_utils.input_validation.core.validation_engine import (
        format_oci_image_ingest_credentials_error,
        logic_oci_image_ingest_credentials,
        schema as validate_against_schema,
    )
    HAS_ENGINE = True
except ImportError:  # jsonschema or the validation package is unavailable
    HAS_ENGINE = False

DOCUMENTATION = r"""
---
module: validate_oci_image_ingest_credentials
short_description: Validate OCI image ingest registry credentials
version_added: "2.3.0"
description:
  - Runs L1 (JSON Schema) and L2 (business logic) validation on the decrypted credentials.
  - Error messages name the field only. Credential values are never returned or logged.
options:
  credentials:
    description: Decrypted credentials mapping (registry_username, registry_password).
    type: dict
    required: true
  schema_path:
    description: Path to oci_image_ingest_credentials.json.
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
- name: Validate stored registry credentials
  validate_oci_image_ingest_credentials:
    credentials: "{{ oci_ingest_credentials }}"
    schema_path: "{{ role_path }}/../../plugins/module_utils/input_validation/schema/oci_image_ingest_credentials.json"
  no_log: true
"""

RETURN = r"""
errors:
  description: Validation errors (field names only, never values).
  returned: failure
  type: list
  elements: str
"""

LOG_NAME = "oci_image_ingest"
FILE_LABEL = "oci_image_ingest_credentials"


def main() -> None:
    """Module entry point."""
    module = AnsibleModule(
        argument_spec={"credentials": {"type": "dict", "required": True, "no_log": True},
                       "schema_path": {"type": "path", "required": True},
                       "log_dir": {"type": "path", "default": ""}},
        supports_check_mode=True,
    )
    if not HAS_ENGINE:
        module.fail_json(msg="python jsonschema library and the utils input validation "
                             "package are required")
    if not os.path.isfile(module.params["schema_path"]):
        module.fail_json(msg="schema_path not found")
    try:
        with open(module.params["schema_path"], encoding="utf-8") as handle:
            schema_def = json.load(handle)
    except json.JSONDecodeError:
        module.fail_json(msg="schema_path is not valid JSON")
    logger = create_logger(module.params["log_dir"], LOG_NAME)
    credentials = module.params["credentials"]
    errors = []
    validate_against_schema(credentials, schema_def, FILE_LABEL, errors, logger,
                            formatter=format_oci_image_ingest_credentials_error)
    if not errors:
        errors = logic_oci_image_ingest_credentials(credentials, logger)
    if errors:
        module.fail_json(msg="oci_image_ingest_credentials validation failed", errors=errors)
    logger.info("oci_image_ingest_credentials validated (values not logged)")
    module.exit_json(changed=False, msg="oci_image_ingest_credentials are valid")


if __name__ == "__main__":
    main()
