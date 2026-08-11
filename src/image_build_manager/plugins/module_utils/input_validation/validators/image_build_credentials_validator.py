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
"""
Image build credentials validator.

This module validates image_build_credentials.yml against
image_build_config.yml for cross-file consistency:
- S3 access credentials when provider is 'powerscale'
- aarch64 SSH password when aarch64 host IP is configured
"""
from ansible.module_utils.input_validation.messages import (  # pylint: disable=E0401
    image_build_messages as msg,
)


def validate(cred_data, config_data, logger=None):
    """
    Validate credential file logic against config.

    Args:
        cred_data (dict): Parsed image_build_credentials.yml content.
        config_data (dict): Parsed image_build_config.yml content.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    errors = []

    s3 = config_data.get("s3_configurations", {})
    provider = s3.get("provider", "")

    if provider == "powerscale":
        s3_access_id = cred_data.get("s3_access_id", "")
        if not s3_access_id or not s3_access_id.strip():
            errors.append(msg.S3_ACCESS_ID_REQUIRED_MSG)
            if logger:
                logger.error(msg.S3_ACCESS_ID_REQUIRED_MSG)

    aarch64_ip = config_data.get("aarch64_inventory_host_ip", "")
    if aarch64_ip and aarch64_ip.strip():
        aarch64_pw = cred_data.get("aarch64_ssh_password", "")
        if not aarch64_pw or not aarch64_pw.strip():
            errors.append(msg.AARCH64_SSH_PASSWORD_REQUIRED_MSG)
            if logger:
                logger.error(msg.AARCH64_SSH_PASSWORD_REQUIRED_MSG)

    return errors
