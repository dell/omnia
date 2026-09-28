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
Collect PXE configuration validator.

This module validates collect_pxe.yml for:
- IP address format validation for each functional group
- Valid functional group names
"""
import re
from ansible.module_utils.input_validation.messages import (  # pylint: disable=E0401
    utils_messages as msg,
)

# Valid functional group names for log collection
VALID_FUNCTIONAL_GROUPS = {
    "service_kube_control_plane_x86_64",
    "service_kube_node_x86_64",
    "slurm_control_node_x86_64",
    "slurm_node_x86_64",
    "slurm_node_aarch64",
    "login_node_x86_64",
    "login_compiler_node_aarch64",
}


def _validate_ip_addresses(config_data, errors, logger=None):
    """
    Validate IP addresses in functional groups.

    Rules:
    - All IP addresses must be valid IPv4 format
    - Reserved IPs (127.0.0.1, 255.255.255.255) are not allowed
    """
    for group_name, ip_list in config_data.items():
        if not isinstance(ip_list, list):
            continue
            
        for ip_address in ip_list:
            if not isinstance(ip_address, str):
                error = f"collect_pxe_config: {group_name} contains non-string value: {ip_address}"
                errors.append(error)
                if logger:
                    logger.error(error)
                continue
            
            # Basic IPv4 validation
            ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ipv4_pattern, ip_address.strip()):
                error = f"collect_pxe_config: {group_name} contains invalid IP address: {ip_address}"
                errors.append(error)
                if logger:
                    logger.error(error)
                continue
            
            # Check for reserved IPs
            reserved_ips = {"127.0.0.1", "255.255.255.255"}
            if ip_address.strip() in reserved_ips:
                error = f"collect_pxe_config: {group_name} contains reserved IP address: {ip_address}"
                errors.append(error)
                if logger:
                    logger.error(error)


def _validate_functional_groups(config_data, errors, logger=None):
    """
    Validate functional group names.

    Rules:
    - All keys must be valid functional group names
    """
    for group_name in config_data.keys():
        if group_name not in VALID_FUNCTIONAL_GROUPS:
            valid_groups = ", ".join(sorted(VALID_FUNCTIONAL_GROUPS))
            error = (
                f"collect_pxe_config: Invalid functional group '{group_name}'. "
                f"Valid groups: {valid_groups}"
            )
            errors.append(error)
            if logger:
                logger.error(error)


def validate(config_data, logger=None):
    """
    Run all L2 validation rules on collect_pxe.yml data.

    Args:
        config_data (dict): Parsed collect_pxe.yml content.
        logger: Optional logger instance.

    Returns:
        list: List of error message strings (empty if valid).
    """
    errors = []
    _validate_functional_groups(config_data, errors, logger)
    _validate_ip_addresses(config_data, errors, logger)
    return errors
