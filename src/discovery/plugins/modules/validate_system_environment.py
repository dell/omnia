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

"""Validate the OIM system environment used by the Discovery domain."""

from __future__ import annotations

import ipaddress
import os
import socket
import subprocess
from typing import Any

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
---
module: validate_system_environment
short_description: Validate the Discovery system environment
version_added: "2.3.0"
description:
  - Performs read-only checks of Omnia environment variables.
  - Optionally compares the configured hostname, domain, and management IPv4
    address with the local OIM host.
  - Optionally verifies that the configured data path exists or has an
    available writable parent directory.
options:
  required_vars:
    description:
      - Environment variables that must be defined and non-empty.
      - Use an empty list when only optional system comparisons are required.
    type: list
    elements: str
    default: []
  validate_hostname:
    description:
      - Compare C(SYSTEM_HOSTNAME) with the local short hostname when the
        variable is defined.
    type: bool
    default: true
  validate_domain:
    description:
      - Compare C(SYSTEM_DOMAIN_NAME) with the local domain when both values
        are available.
    type: bool
    default: true
  validate_ip:
    description:
      - Verify that C(SYSTEM_ADMIN_NIC_IPV4) is a local IPv4 address when the
        variable is defined.
    type: bool
    default: true
  validate_paths:
    description:
      - Validate the resolved Discovery component data path.
    type: bool
    default: true
  data_path:
    description:
      - Resolved Discovery component data path to validate.
      - When omitted, C(DISCOVERY_DATA_PATH) is used, falling back to the
        C(discovery) directory below C(OMNIA_DATA_PATH).
    type: str
    default: ""
author:
  - Dell Technologies (@dell)
"""

EXAMPLES = r"""
- name: Validate the Discovery system environment
  omnia.discovery.validate_system_environment:
    required_vars: []
    validate_hostname: false
    validate_domain: false
    validate_ip: false
    validate_paths: true
    data_path: "{{ discovery_data_path }}"
  register: discovery_environment
"""

RETURN = r"""
valid:
  description: Whether every executed validation passed.
  returned: always
  type: bool
checks:
  description: Results for each executed validation.
  returned: always
  type: list
  elements: dict
  contains:
    name:
      description: Validation identifier.
      type: str
    expected:
      description: Expected value or condition.
      type: str
    actual:
      description: Observed value or condition.
      type: str
    passed:
      description: Whether this validation passed.
      type: bool
    message:
      description: Human-readable validation result.
      type: str
msg:
  description: Overall validation result.
  returned: always
  type: str
"""


def _run_read_only_command(arguments: list[str]) -> str:
    """Run a fixed read-only command and return its stripped output."""
    try:
        result = subprocess.run(
            arguments,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            shell=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _system_hostname() -> str:
    """Return the local short hostname."""
    return _run_read_only_command(["hostname", "-s"]) or socket.gethostname().split(".")[0]


def _system_domain() -> str:
    """Return the local DNS domain when available."""
    return _run_read_only_command(["hostname", "-d"])


def _local_ipv4_addresses() -> list[str]:
    """Return IPv4 addresses assigned to local interfaces."""
    output = _run_read_only_command(["ip", "-4", "-o", "addr", "show"])
    addresses: list[str] = []
    for line in output.splitlines():
        fields = line.split()
        for index, field in enumerate(fields):
            if field == "inet" and index + 1 < len(fields):
                addresses.append(fields[index + 1].split("/", maxsplit=1)[0])
    return addresses


def _required_variable_check(name: str) -> dict[str, Any]:
    """Build the result for one required environment variable."""
    value = os.environ.get(name, "")
    passed = bool(value)
    return {
        "name": f"env_{name}",
        "expected": f"{name} is defined and non-empty",
        "actual": "(set)" if passed else "(not set)",
        "passed": passed,
        "message": (
            f"{name} is configured"
            if passed
            else f"{name} is not set; configure it before running Discovery"
        ),
    }


def _hostname_check(configured_hostname: str) -> dict[str, Any]:
    """Compare the configured and local short hostnames."""
    actual_hostname = _system_hostname()
    passed = configured_hostname == actual_hostname
    return {
        "name": "validate_hostname",
        "expected": configured_hostname,
        "actual": actual_hostname,
        "passed": passed,
        "message": (
            f"Configured hostname matches the OIM host: {configured_hostname}"
            if passed
            else (
                f"SYSTEM_HOSTNAME '{configured_hostname}' does not match "
                f"the local short hostname '{actual_hostname}'"
            )
        ),
    }


def _domain_check(configured_domain: str) -> dict[str, Any]:
    """Compare the configured and local domains when the latter is available."""
    actual_domain = _system_domain()
    if not actual_domain:
        return {
            "name": "validate_domain",
            "expected": configured_domain,
            "actual": "(local domain unavailable)",
            "passed": True,
            "message": "Local domain is unavailable; domain comparison was skipped",
        }

    passed = configured_domain == actual_domain
    return {
        "name": "validate_domain",
        "expected": configured_domain,
        "actual": actual_domain,
        "passed": passed,
        "message": (
            f"Configured domain matches the OIM host: {configured_domain}"
            if passed
            else (
                f"SYSTEM_DOMAIN_NAME '{configured_domain}' does not match "
                f"the local domain '{actual_domain}'"
            )
        ),
    }


def _ip_check(configured_ip: str) -> dict[str, Any]:
    """Verify that the configured IPv4 address belongs to the local host."""
    try:
        parsed_ip = ipaddress.ip_address(configured_ip)
    except ValueError:
        return {
            "name": "validate_ip_format",
            "expected": "a valid IPv4 address",
            "actual": configured_ip,
            "passed": False,
            "message": (
                f"SYSTEM_ADMIN_NIC_IPV4 '{configured_ip}' is not a valid IPv4 address"
            ),
        }

    if parsed_ip.version != 4:
        return {
            "name": "validate_ip_format",
            "expected": "a valid IPv4 address",
            "actual": configured_ip,
            "passed": False,
            "message": (
                f"SYSTEM_ADMIN_NIC_IPV4 '{configured_ip}' is not an IPv4 address"
            ),
        }

    local_addresses = _local_ipv4_addresses()
    passed = configured_ip in local_addresses
    actual = ", ".join(local_addresses) if local_addresses else "(none found)"
    return {
        "name": "validate_ip_on_nic",
        "expected": configured_ip,
        "actual": actual,
        "passed": passed,
        "message": (
            f"Configured management IP is assigned locally: {configured_ip}"
            if passed
            else (
                f"SYSTEM_ADMIN_NIC_IPV4 '{configured_ip}' is not assigned "
                f"to a local interface; local addresses: {actual}"
            )
        ),
    }


def _data_path_check(configured_path: str) -> dict[str, Any]:
    """Validate the Discovery data path without modifying it."""
    if not os.path.isabs(configured_path):
        return {
            "name": "validate_data_path",
            "expected": "an absolute path",
            "actual": configured_path,
            "passed": False,
            "message": "Discovery data path must be an absolute path",
        }

    if os.path.isdir(configured_path):
        return {
            "name": "validate_data_path",
            "expected": f"{configured_path} is a directory",
            "actual": f"{configured_path} is a directory",
            "passed": True,
            "message": f"Discovery data path exists: {configured_path}",
        }

    if os.path.exists(configured_path):
        return {
            "name": "validate_data_path",
            "expected": f"{configured_path} is a directory",
            "actual": f"{configured_path} exists but is not a directory",
            "passed": False,
            "message": (
                f"Discovery data path '{configured_path}' exists but is not "
                "a directory"
            ),
        }

    parent = os.path.dirname(configured_path)
    parent_available = os.path.isdir(parent) and os.access(parent, os.W_OK)
    return {
        "name": "validate_data_path",
        "expected": f"{configured_path} exists or its parent is writable",
        "actual": (
            f"parent {parent} is writable"
            if parent_available
            else f"parent {parent} is unavailable or not writable"
        ),
        "passed": parent_available,
        "message": (
            f"Discovery data path can be created below writable parent {parent}"
            if parent_available
            else (
                f"Discovery data path '{configured_path}' does not exist and "
                f"its parent '{parent}' is unavailable or not writable"
            )
        ),
    }


def main() -> None:
    """Validate the requested environment properties."""
    module = AnsibleModule(
        argument_spec={
            "required_vars": {
                "type": "list",
                "elements": "str",
                "default": [],
            },
            "validate_hostname": {"type": "bool", "default": True},
            "validate_domain": {"type": "bool", "default": True},
            "validate_ip": {"type": "bool", "default": True},
            "validate_paths": {"type": "bool", "default": True},
            "data_path": {"type": "str", "default": ""},
        },
        supports_check_mode=True,
    )

    checks = [
        _required_variable_check(variable_name)
        for variable_name in module.params["required_vars"]
    ]

    configured_hostname = os.environ.get("SYSTEM_HOSTNAME", "")
    if module.params["validate_hostname"] and configured_hostname:
        checks.append(_hostname_check(configured_hostname))

    configured_domain = os.environ.get("SYSTEM_DOMAIN_NAME", "")
    if module.params["validate_domain"] and configured_domain:
        checks.append(_domain_check(configured_domain))

    configured_ip = os.environ.get("SYSTEM_ADMIN_NIC_IPV4", "")
    if module.params["validate_ip"] and configured_ip:
        checks.append(_ip_check(configured_ip))

    configured_path = module.params["data_path"]
    if not configured_path:
        configured_path = os.environ.get("DISCOVERY_DATA_PATH", "")
    if not configured_path:
        omnia_data_path = os.environ.get("OMNIA_DATA_PATH", "")
        if omnia_data_path:
            configured_path = os.path.join(omnia_data_path, "discovery")
    if module.params["validate_paths"] and configured_path:
        checks.append(_data_path_check(configured_path))

    failed_checks = [check for check in checks if not check["passed"]]
    if failed_checks:
        module.fail_json(
            changed=False,
            valid=False,
            checks=checks,
            msg="Environment validation failed: "
            + "; ".join(check["message"] for check in failed_checks),
        )

    module.exit_json(
        changed=False,
        valid=True,
        checks=checks,
        msg=f"All {len(checks)} requested environment checks passed",
    )


if __name__ == "__main__":
    main()
