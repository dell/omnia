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

"""Validate that required Omnia environment variables are configured and
consistent with the actual system state (hostname, admin IP, paths).

This module can be used in any domain's setup role as a common precheck.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
from typing import Any

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
---
module: validate_system_environment
short_description: Validate Omnia environment variables against system state
description:
  - Checks that all required environment variables are set.
  - Cross-validates env vars against actual system details (hostname, IP on NIC, paths).
  - Returns structured per-check results with expected/actual values.
options:
  required_vars:
    description: List of environment variable names that MUST be set (non-empty).
    type: list
    elements: str
    default:
      - SYSTEM_ADMIN_NIC_IPV4
      - SYSTEM_HOSTNAME
      - SYSTEM_DOMAIN_NAME
      - OMNIA_DATA_PATH
  validate_hostname:
    description: Cross-check SYSTEM_HOSTNAME against hostname -s.
    type: bool
    default: true
  validate_domain:
    description: Cross-check SYSTEM_DOMAIN_NAME against hostname -d.
    type: bool
    default: true
  validate_ip:
    description: Cross-check SYSTEM_ADMIN_NIC_IPV4 is present on a local NIC.
    type: bool
    default: true
  validate_paths:
    description: Verify OMNIA_DATA_PATH directory exists or is creatable.
    type: bool
    default: true
author:
  - Dell Omnia Team
"""

EXAMPLES = r"""
- name: Validate system environment
  omnia.image_build.validate_system_environment:
    required_vars:
      - SYSTEM_ADMIN_NIC_IPV4
      - SYSTEM_HOSTNAME
      - SYSTEM_DOMAIN_NAME
      - OMNIA_DATA_PATH
    validate_hostname: true
    validate_ip: true
    validate_paths: true
  register: env_check

- name: Display validation result
  ansible.builtin.debug:
    msg: "Environment {{ 'valid' if env_check.valid else 'invalid' }}"
"""

RETURN = r"""
valid:
  description: Whether all checks passed.
  type: bool
checks:
  description: Per-check result list.
  type: list
  elements: dict
  contains:
    name:
      description: Check identifier.
      type: str
    expected:
      description: Expected value from env var.
      type: str
    actual:
      description: Actual value from system.
      type: str
    passed:
      description: Whether this check passed.
      type: bool
    message:
      description: Human-readable result.
      type: str
"""

# IPv4 regex
_IPV4_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
)


def _get_system_hostname() -> str:
    """Return the short hostname via ``hostname -s``."""
    try:
        result = subprocess.run(
            ["hostname", "-s"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # Fallback to socket
    return socket.gethostname().split(".")[0]


def _get_system_domain() -> str:
    """Return the domain name via ``hostname -d``."""
    try:
        result = subprocess.run(
            ["hostname", "-d"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ""


def _get_local_ips() -> list[str]:
    """Return list of IPv4 addresses on local network interfaces."""
    ips: list[str] = []
    try:
        result = subprocess.run(
            ["ip", "-4", "-o", "addr", "show"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            for i, part in enumerate(parts):
                if part == "inet" and i + 1 < len(parts):
                    ip_cidr = parts[i + 1]
                    ips.append(ip_cidr.split("/")[0])
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ips


def _check_env_var(name: str) -> dict[str, Any]:
    """Check a single env var is set and non-empty."""
    value = os.environ.get(name, "")
    passed = len(value) > 0
    return {
        "name": f"env_{name}",
        "expected": f"{name} is set and non-empty",
        "actual": value if passed else "(not set)",
        "passed": passed,
        "message": f"{name} is configured" if passed else f"{name} is NOT set. Export it before running.",
    }


def _check_hostname(env_hostname: str) -> dict[str, Any]:
    """Cross-validate SYSTEM_HOSTNAME against ``hostname -s``."""
    system_hostname = _get_system_hostname()
    passed = env_hostname == system_hostname
    return {
        "name": "validate_hostname",
        "expected": env_hostname,
        "actual": system_hostname,
        "passed": passed,
        "message": (
            f"Hostname matches (hostname -s): {env_hostname}"
            if passed
            else (
                f"SYSTEM_HOSTNAME '{env_hostname}' does not match "
                f"hostname -s '{system_hostname}'. "
                f"Fix: hostnamectl set-hostname {env_hostname} or update omnia.env"
            )
        ),
    }


def _check_domain(env_domain: str) -> dict[str, Any]:
    """Cross-validate SYSTEM_DOMAIN_NAME against ``hostname -d``."""
    system_domain = _get_system_domain()
    if not system_domain:
        return {
            "name": "validate_domain",
            "expected": env_domain,
            "actual": "(hostname -d unavailable)",
            "passed": True,
            "message": f"hostname -d unavailable — skipping domain check (configured: {env_domain})",
        }
    passed = env_domain == system_domain
    return {
        "name": "validate_domain",
        "expected": env_domain,
        "actual": system_domain,
        "passed": passed,
        "message": (
            f"Domain matches (hostname -d): {env_domain}"
            if passed
            else (
                f"SYSTEM_DOMAIN_NAME '{env_domain}' does not match "
                f"hostname -d '{system_domain}'. "
                f"Fix: update omnia.env or "
                f"hostnamectl set-hostname {{hostname}}.{env_domain}"
            )
        ),
    }


def _check_ip_on_nic(env_ip: str) -> dict[str, Any]:
    """Cross-validate SYSTEM_ADMIN_NIC_IPV4 exists on a local NIC."""
    if not _IPV4_RE.match(env_ip):
        return {
            "name": "validate_ip_format",
            "expected": "Valid IPv4 address",
            "actual": env_ip,
            "passed": False,
            "message": f"SYSTEM_ADMIN_NIC_IPV4 '{env_ip}' is not a valid IPv4 address",
        }

    local_ips = _get_local_ips()
    passed = env_ip in local_ips
    return {
        "name": "validate_ip_on_nic",
        "expected": env_ip,
        "actual": ", ".join(local_ips) if local_ips else "(no IPs found)",
        "passed": passed,
        "message": (
            f"Admin IP {env_ip} found on local NIC"
            if passed
            else f"SYSTEM_ADMIN_NIC_IPV4 '{env_ip}' not found on any local NIC. Available: {', '.join(local_ips)}"
        ),
    }


def _check_data_path(env_path: str) -> dict[str, Any]:
    """Verify OMNIA_DATA_PATH exists or parent is writable."""
    if os.path.isdir(env_path):
        return {
            "name": "validate_data_path",
            "expected": f"{env_path} exists",
            "actual": f"{env_path} exists",
            "passed": True,
            "message": f"OMNIA_DATA_PATH {env_path} exists",
        }

    parent = os.path.dirname(env_path)
    parent_exists = os.path.isdir(parent)
    return {
        "name": "validate_data_path",
        "expected": f"{env_path} exists or parent is writable",
        "actual": f"parent {parent} {'exists' if parent_exists else 'missing'}",
        "passed": parent_exists,
        "message": (
            f"OMNIA_DATA_PATH {env_path} does not exist yet but parent {parent} is available"
            if parent_exists
            else f"OMNIA_DATA_PATH '{env_path}' and parent '{parent}' do not exist"
        ),
    }


def main() -> None:
    """Module entry point."""
    module = AnsibleModule(
        argument_spec=dict(
            required_vars=dict(
                type="list", elements="str",
                default=["SYSTEM_ADMIN_NIC_IPV4", "SYSTEM_HOSTNAME",
                         "SYSTEM_DOMAIN_NAME", "OMNIA_DATA_PATH"],
            ),
            validate_hostname=dict(type="bool", default=True),
            validate_domain=dict(type="bool", default=True),
            validate_ip=dict(type="bool", default=True),
            validate_paths=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
    )

    required_vars: list[str] = module.params["required_vars"]
    validate_hostname: bool = module.params["validate_hostname"]
    validate_domain: bool = module.params["validate_domain"]
    validate_ip: bool = module.params["validate_ip"]
    validate_paths: bool = module.params["validate_paths"]

    checks: list[dict[str, Any]] = []

    # 1. Check all required env vars are set
    for var_name in required_vars:
        checks.append(_check_env_var(var_name))

    # 2. Cross-validate hostname (hostname -s)
    env_hostname = os.environ.get("SYSTEM_HOSTNAME", "")
    if validate_hostname and env_hostname:
        checks.append(_check_hostname(env_hostname))

    # 3. Cross-validate domain (hostname -d)
    env_domain = os.environ.get("SYSTEM_DOMAIN_NAME", "")
    if validate_domain and env_domain:
        checks.append(_check_domain(env_domain))

    # 4. Cross-validate admin IP is on a local NIC
    env_ip = os.environ.get("SYSTEM_ADMIN_NIC_IPV4", "")
    if validate_ip and env_ip:
        checks.append(_check_ip_on_nic(env_ip))

    # 5. Validate data path
    env_path = os.environ.get("OMNIA_DATA_PATH", "/opt/omnia")
    if validate_paths and env_path:
        checks.append(_check_data_path(env_path))

    all_passed = all(c["passed"] for c in checks)
    failed_checks = [c for c in checks if not c["passed"]]

    if all_passed:
        module.exit_json(
            changed=False,
            valid=True,
            checks=checks,
            msg=f"All {len(checks)} environment checks passed",
        )
    else:
        failed_msgs = "; ".join(c["message"] for c in failed_checks)
        module.fail_json(
            msg=f"Environment validation failed: {failed_msgs}",
            valid=False,
            checks=checks,
        )


if __name__ == "__main__":
    main()
