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
Install OS credentials validator.

This module validates install_os_credentials.yml for:
- Required credential fields presence
- Basic credential field validation
"""
from ansible.module_utils.input_validation.messages import (  # pylint: disable=E0401
    utils_messages as msg,
)


def _validate_required_credentials(config_data, errors, logger=None):
    """
    Validate required credential fields.

    Rules:
    - bmc_username is required
    - bmc_password is required
    - os_root_password is required
    """
    required_fields = ["bmc_username", "bmc_password", "os_root_password"]
    
    for field in required_fields:
        value = config_data.get(field, "")
        if not value or not value.strip():
            error = f"install_os_credentials: Required field '{field}' is missing or empty"
            errors.append(error)
            if logger:
                logger.error(error)


def validate(config_data, logger=None):
    """
    Run all L2 validation rules on install_os_credentials.yml data.

    Args:
        config_data (dict): Parsed install_os_credentials.yml content.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    errors = []
    _validate_required_credentials(config_data, errors, logger)
    return errors
