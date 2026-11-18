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

"""Append a line to the OCI image ingest log under utils/log/<project>/."""

from __future__ import annotations

from ansible.module_utils.basic import AnsibleModule

try:
    from ansible.module_utils.input_validation.core.utils import create_logger
    HAS_LOGGER = True
except ImportError:
    HAS_LOGGER = False

DOCUMENTATION = r"""
---
module: oci_ingest_log
short_description: Write a message to the OCI image ingest log
version_added: "2.3.0"
description:
  - Appends a timestamped line to C(oci_image_ingest.log) in the given directory.
  - Callers must pass only non-secret values (never credentials).
options:
  log_dir:
    description: Log directory, normally C(${OMNIA_DATA_PATH}/utils/log/<project>).
    type: path
    required: true
  message:
    description: Message to log.
    type: str
    required: true
  level:
    description: Log level.
    type: str
    choices: [info, warning, error]
    default: info
author:
  - Dell Omnia Team
"""

EXAMPLES = r"""
- name: Log the pinned digest
  oci_ingest_log:
    log_dir: "{{ oci_ingest_log_dir }}"
    message: "image={{ image }} digest={{ digest }}"
"""

RETURN = r"""
log_file:
  description: Path of the log file written.
  returned: always
  type: str
"""

LOG_NAME = "oci_image_ingest"


def main() -> None:
    """Module entry point."""
    module = AnsibleModule(
        argument_spec={"log_dir": {"type": "path", "required": True},
                       "message": {"type": "str", "required": True},
                       "level": {"type": "str", "default": "info",
                                 "choices": ["info", "warning", "error"]}},
        supports_check_mode=False,
    )
    if not HAS_LOGGER:
        module.fail_json(msg="the utils input validation package is required")
    logger = create_logger(module.params["log_dir"], LOG_NAME)
    if not logger.log_file:
        module.fail_json(msg="cannot write the OCI image ingest log directory")
    getattr(logger, module.params["level"])(module.params["message"].replace("\n", " "))
    module.exit_json(changed=False, log_file=logger.log_file)


if __name__ == "__main__":
    main()
