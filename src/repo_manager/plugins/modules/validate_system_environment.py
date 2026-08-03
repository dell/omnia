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

"""
Ansible module to validate Omnia system environment variables.

This module validates that required environment variables are set and
conform to expected formats. It is designed to be used in the setup
role of any Omnia domain.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r'''
---
module: validate_system_environment
short_description: Validate Omnia system environment variables
version_added: "2.0.0"
description:
    - Validates that required Omnia environment variables are set.
    - Checks format of hostname, IPv4 address, and paths.
    - Returns detailed error messages for validation failures.
options:
    required_vars:
        description:
            - List of environment variable names that must be set.
        type: list
        elements: str
        required: true
    validate_hostname:
        description:
            - Whether to validate SYSTEM_HOSTNAME format.
        type: bool
        default: false
    validate_ip:
        description:
            - Whether to validate SYSTEM_ADMIN_NIC_IPV4 as valid IPv4.
        type: bool
        default: false
    validate_paths:
        description:
            - Whether to validate OMNIA_DATA_PATH as absolute path.
        type: bool
        default: false
author:
    - Dell Technologies (@dell)
'''

EXAMPLES = r'''
- name: Validate system environment
  validate_system_environment:
    required_vars:
      - SYSTEM_ADMIN_NIC_IPV4
      - OMNIA_DATA_PATH
    validate_hostname: true
    validate_ip: true
    validate_paths: true
  register: env_check

- name: Fail if environment validation fails
  ansible.builtin.fail:
    msg: "{{ env_check.errors | join('; ') }}"
  when: env_check.failed | default(false)
'''

RETURN = r'''
validated:
    description: Whether all validations passed.
    type: bool
    returned: always
errors:
    description: List of validation error messages.
    type: list
    elements: str
    returned: always
env_values:
    description: Dictionary of environment variable values that were checked.
    type: dict
    returned: always
'''

import os
import re
import socket

from ansible.module_utils.basic import AnsibleModule


def validate_hostname_format(hostname: str) -> tuple[bool, str]:
    """
    Validate hostname format.

    Args:
        hostname: The hostname to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not hostname:
        return False, "SYSTEM_HOSTNAME is empty"

    # Hostname regex: alphanumeric with hyphens, no leading/trailing hyphens
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$'
    if not re.match(pattern, hostname):
        return False, (
            f"Invalid SYSTEM_HOSTNAME format: '{hostname}'. "
            "Must be alphanumeric with hyphens only, no leading/trailing hyphens."
        )

    return True, ""


def validate_ipv4_address(ip_address: str) -> tuple[bool, str]:
    """
    Validate IPv4 address format.

    Args:
        ip_address: The IP address to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not ip_address:
        return False, "SYSTEM_ADMIN_NIC_IPV4 is empty"

    try:
        socket.inet_aton(ip_address)
        # Additional check: inet_aton accepts some invalid formats
        parts = ip_address.split('.')
        if len(parts) != 4:
            raise OSError("Invalid IPv4 format")
        for part in parts:
            if not 0 <= int(part) <= 255:
                raise OSError("Invalid IPv4 octet")
        return True, ""
    except (OSError, ValueError):
        return False, f"Invalid SYSTEM_ADMIN_NIC_IPV4: '{ip_address}'. Must be a valid IPv4 address."


def validate_absolute_path(path: str) -> tuple[bool, str]:
    """
    Validate that a path is absolute.

    Args:
        path: The path to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not path:
        return False, "OMNIA_DATA_PATH is empty"

    if not path.startswith('/'):
        return False, f"Invalid OMNIA_DATA_PATH: '{path}'. Must be an absolute path starting with '/'."

    return True, ""


def main():
    """Main module entry point."""
    module = AnsibleModule(
        argument_spec={
            'required_vars': {
                'type': 'list',
                'elements': 'str',
                'required': True
            },
            'validate_hostname': {
                'type': 'bool',
                'default': False
            },
            'validate_ip': {
                'type': 'bool',
                'default': False
            },
            'validate_paths': {
                'type': 'bool',
                'default': False
            }
        },
        supports_check_mode=True
    )

    required_vars = module.params['required_vars']
    validate_hostname = module.params['validate_hostname']
    validate_ip = module.params['validate_ip']
    validate_paths = module.params['validate_paths']

    errors = []
    env_values = {}

    # Check required environment variables
    for var_name in required_vars:
        value = os.environ.get(var_name, '')
        env_values[var_name] = value
        if not value:
            errors.append(f"Required environment variable not set: {var_name}")

    # Validate hostname format
    if validate_hostname:
        hostname = os.environ.get('SYSTEM_HOSTNAME', '')
        env_values['SYSTEM_HOSTNAME'] = hostname
        if hostname:
            is_valid, error_msg = validate_hostname_format(hostname)
            if not is_valid:
                errors.append(error_msg)

    # Validate IPv4 address
    if validate_ip:
        ip_address = os.environ.get('SYSTEM_ADMIN_NIC_IPV4', '')
        env_values['SYSTEM_ADMIN_NIC_IPV4'] = ip_address
        if ip_address:
            is_valid, error_msg = validate_ipv4_address(ip_address)
            if not is_valid:
                errors.append(error_msg)

    # Validate paths
    if validate_paths:
        data_path = os.environ.get('OMNIA_DATA_PATH', '')
        env_values['OMNIA_DATA_PATH'] = data_path
        if data_path:
            is_valid, error_msg = validate_absolute_path(data_path)
            if not is_valid:
                errors.append(error_msg)

    # Return results
    if errors:
        module.fail_json(
            msg="Environment validation failed",
            validated=False,
            errors=errors,
            env_values=env_values
        )
    else:
        module.exit_json(
            changed=False,
            validated=True,
            errors=[],
            env_values=env_values
        )


if __name__ == '__main__':
    main()
