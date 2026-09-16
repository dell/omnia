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
Install OS configuration validator.

This module validates install_os_config.yml for:
- Required field presence based on execution mode
- IP address format validation
- File path accessibility
- Kickstart delivery method validation
"""
import os
import re
from ansible.module_utils.input_validation.messages import (  # pylint: disable=E0401
    utils_messages as msg,
)


def _validate_source_iso(config_data, errors, logger=None):
    """
    Validate source ISO configuration.

    Rules:
    - source_iso_path is required for build_iso, generate_ks, and end-to-end modes
    - source_iso_path must exist and be accessible
    """
    source_iso = config_data.get("source_iso_path", "")
    if not source_iso or not source_iso.strip():
        errors.append(msg.SOURCE_ISO_REQUIRED_MSG)
        if logger:
            logger.error(msg.SOURCE_ISO_REQUIRED_MSG)
        return

    if not os.path.exists(source_iso):
        errors.append(msg.SOURCE_ISO_NOT_FOUND_MSG)
        if logger:
            logger.error(msg.SOURCE_ISO_NOT_FOUND_MSG)


def _validate_custom_iso(config_data, errors, logger=None):
    """
    Validate custom ISO path configuration.

    Rules:
    - custom_iso_path is required for build_iso, deploy, and end-to-end modes
    - Must be in NFS format (server:/path) or local path
    """
    custom_iso = config_data.get("custom_iso_path", "")
    if not custom_iso or not custom_iso.strip():
        errors.append(msg.CUSTOM_ISO_REQUIRED_MSG)
        if logger:
            logger.error(msg.CUSTOM_ISO_REQUIRED_MSG)


def _validate_target_bmc_ip(config_data, errors, logger=None):
    """
    Validate target BMC IP configuration.

    Rules:
    - target_bmc_ip is required for deploy and end-to-end modes
    - Must be a valid IPv4 address format
    """
    bmc_ip = config_data.get("target_bmc_ip", "")
    if not bmc_ip or not bmc_ip.strip():
        errors.append(msg.TARGET_BMC_IP_REQUIRED_MSG)
        if logger:
            logger.error(msg.TARGET_BMC_IP_REQUIRED_MSG)
        return

    # Basic IPv4 validation
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(ipv4_pattern, bmc_ip.strip()):
        errors.append(msg.TARGET_BMC_IP_INVALID_MSG)
        if logger:
            logger.error(msg.TARGET_BMC_IP_INVALID_MSG)


def _validate_target_admin_ip(config_data, errors, logger=None):
    """
    Validate target admin IP configuration.

    Rules:
    - target_admin_ip must be a valid IPv4 address format if provided
    """
    admin_ip = config_data.get("target_admin_ip", "")
    if not admin_ip or not admin_ip.strip():
        return  # Optional field

    # Basic IPv4 validation
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(ipv4_pattern, admin_ip.strip()):
        errors.append(msg.TARGET_ADMIN_IP_INVALID_MSG)
        if logger:
            logger.error(msg.TARGET_ADMIN_IP_INVALID_MSG)


def _validate_kickstart_delivery(config_data, errors, logger=None):
    """
    Validate kickstart delivery method.

    Rules:
    - kickstart_delivery_method must be 'embedded' or 'nfs'
    """
    delivery_method = config_data.get("kickstart_delivery_method", "")
    if delivery_method and delivery_method.strip() not in ("embedded", "nfs"):
        errors.append(msg.KICKSTART_DELIVERY_INVALID_MSG)
        if logger:
            logger.error(msg.KICKSTART_DELIVERY_INVALID_MSG)


def _validate_ssh_key(config_data, errors, logger=None):
    """
    Validate SSH public key path.

    Rules:
    - ssh_public_key_path must exist if provided
    """
    ssh_key_path = config_data.get("ssh_public_key_path", "")
    if ssh_key_path and ssh_key_path.strip() and not os.path.exists(ssh_key_path):
        errors.append(msg.SSH_KEY_NOT_FOUND_MSG)
        if logger:
            logger.error(msg.SSH_KEY_NOT_FOUND_MSG)


def validate(config_data, logger=None):
    """
    Run all L2 validation rules on install_os_config.yml data.

    Args:
        config_data (dict): Parsed install_os_config.yml content.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    errors = []
    _validate_source_iso(config_data, errors, logger)
    _validate_custom_iso(config_data, errors, logger)
    _validate_target_bmc_ip(config_data, errors, logger)
    _validate_target_admin_ip(config_data, errors, logger)
    _validate_kickstart_delivery(config_data, errors, logger)
    _validate_ssh_key(config_data, errors, logger)
    return errors
