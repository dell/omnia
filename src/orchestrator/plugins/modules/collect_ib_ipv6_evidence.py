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
"""Collect physical IPoIB IPv6 release evidence package (ER-ORCH-005, Story 4).

Gathers hardware/software matrix dimensions from the target node:
- ConnectX HCA model, firmware, driver version
- IB switch (from ibstat / ibnetdiscover)
- RHEL version, kernel, NetworkManager version
- Architecture (x86_64 / aarch64)
- IPoIB mode, MTU, P_Key, topology
- OpenSM version and state
- Timestamp and build identity

Produces a structured JSON evidence package for release gate attestation.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from typing import Any

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
---
module: collect_ib_ipv6_evidence
short_description: Collect physical IPoIB IPv6 release evidence
version_added: "2.3.0"
description:
  - Gathers hardware and software matrix dimensions from the target node.
  - Produces a structured JSON evidence package.
  - Runs on each physical target node in the release matrix.
options:
  node_id:
    description: Node identifier (xname or hostname).
    required: true
    type: str
  build_id:
    description: Build identifier for the release candidate.
    required: true
    type: str
  interfaces:
    description: List of IPoIB interface names to collect evidence for.
    required: true
    type: list
    elements: str
  output_dir:
    description: Directory to write the evidence JSON.
    required: true
    type: str
  test_results:
    description: Dict of test case results (TC-ID to pass/fail).
    required: false
    type: dict
    default: {}
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Collect IPoIB IPv6 release evidence
  omnia.orchestrator.collect_ib_ipv6_evidence:
    node_id: "{{ inventory_hostname }}"
    build_id: "{{ omnia_build_id }}"
    interfaces: ["ib0"]
    output_dir: "{{ orchestrator_output_dir }}/evidence"
    test_results: "{{ ib_ipv6_test_results | default({}) }}"
  register: ib_ipv6_evidence
'''

RETURN = r'''
evidence:
  description: Complete evidence package as structured dict.
  returned: always
  type: dict
evidence_file:
  description: Path to the written evidence JSON file.
  returned: always
  type: str
matrix_dimensions:
  description: Hardware/software matrix dimensions collected.
  returned: always
  type: dict
'''


def _run_cmd(argv: list[str]) -> str:
    """Run a command and return stdout (empty on failure)."""
    try:
        result = subprocess.run(
            argv, capture_output=True,
            text=True, timeout=30, check=False,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        return ""


def _read_sysfs(path: str) -> str:
    """Read a sysfs file and return its content (empty on failure)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def _collect_hca_info() -> dict[str, str]:
    """Collect ConnectX HCA model, firmware, and driver."""
    ibstat = _run_cmd(["ibstat", "-s"])
    hca_model = ""
    firmware = ""
    for line in ibstat.splitlines():
        if "CA" in line and "'" in line:
            hca_model = line.split("'")[1] if "'" in line else line.strip()
        if "firmware" in line.lower():
            firmware = line.split(":")[-1].strip() if ":" in line else ""

    # Fallback: try lspci
    if not hca_model:
        lspci = _run_cmd(["lspci"])
        for line in lspci.splitlines():
            if "mellanox" in line.lower():
                hca_model = line.strip()
                break
        if not hca_model:
            hca_model = "unknown"

    modinfo = _run_cmd(["modinfo", "mlx5_core"])
    driver = ""
    for line in modinfo.splitlines():
        if line.startswith("version:"):
            driver = line.split(None, 1)[-1].strip()
            break

    return {
        "hca_model": hca_model or "unknown",
        "firmware": firmware or "unknown",
        "driver_version": driver or "unknown",
    }


def _collect_ib_switch_info() -> dict[str, str]:
    """Collect IB switch info from ibnetdiscover."""
    raw = _run_cmd(["ibnetdiscover"])
    switch_info = ""
    for line in raw.splitlines():
        if "switch" in line.lower():
            switch_info = line.strip()
            break
    return {
        "switch_description": switch_info or "not available (requires ibnetdiscover)",
    }


def _collect_os_info() -> dict[str, str]:
    """Collect OS, kernel, NM version, architecture."""
    os_release = _read_sysfs("/etc/redhat-release")
    if not os_release:
        raw = _read_sysfs("/etc/os-release")
        for line in raw.splitlines():
            if line.startswith("PRETTY_NAME="):
                os_release = line.split("=", 1)[1].strip().strip('"')
                break

    kernel = _run_cmd(["uname", "-r"])
    arch = platform.machine()
    nm_version = _run_cmd(["nmcli", "--version"])

    return {
        "os_release": os_release or "unknown",
        "kernel": kernel or "unknown",
        "architecture": arch or "unknown",
        "nm_version": nm_version or "unknown",
    }


def _collect_ipoib_info(interface: str) -> dict[str, Any]:
    """Collect IPoIB-specific info for an interface."""
    sysfs_base = f"/sys/class/net/{interface}"
    mode = _read_sysfs(f"{sysfs_base}/mode")
    mtu = _read_sysfs(f"{sysfs_base}/mtu")
    pkey = _read_sysfs(f"{sysfs_base}/pkey")
    state = _read_sysfs(f"{sysfs_base}/operstate")
    # Get addresses
    raw_addrs = _run_cmd(
        ["ip", "-6", "addr", "show", "dev", interface, "scope", "global"]
    )
    addrs = [
        tok.split("/")[0]
        for line in raw_addrs.splitlines()
        if "inet6" in line
        for tok in line.split()
        if ":" in tok and "/" in tok
    ]

    return {
        "interface": interface,
        "ipoib_mode": mode or "unknown",
        "mtu": mtu or "unknown",
        "pkey": pkey or "unknown",
        "operstate": state or "unknown",
        "ipv6_addresses": addrs,
    }


def _collect_opensm_info() -> dict[str, str]:
    """Collect OpenSM version and state."""
    version = _run_cmd(["opensm", "--version"])
    state = _run_cmd(["systemctl", "is-active", "opensm"])

    return {
        "opensm_version": version or "unknown",
        "opensm_state": state or "unknown",
    }


def run_module() -> None:
    """Entry point for the Ansible module."""
    module = AnsibleModule(
        argument_spec={
            "node_id": {"type": "str", "required": True},
            "build_id": {"type": "str", "required": True},
            "interfaces": {
                "type": "list", "elements": "str", "required": True,
            },
            "output_dir": {"type": "str", "required": True},
            "test_results": {
                "type": "dict", "required": False, "default": {},
            },
        },
        supports_check_mode=True,
    )
    node_id = module.params["node_id"]
    build_id = module.params["build_id"]
    interfaces = module.params["interfaces"]
    output_dir = os.path.realpath(module.params["output_dir"])
    test_results = module.params["test_results"]

    os.makedirs(output_dir, mode=0o755, exist_ok=True)

    # Collect all matrix dimensions
    hca = _collect_hca_info()
    switch = _collect_ib_switch_info()
    os_info = _collect_os_info()
    opensm = _collect_opensm_info()

    ipoib_interfaces = []
    for iface in interfaces:
        ipoib_interfaces.append(_collect_ipoib_info(iface))

    matrix = {
        **hca,
        **switch,
        **os_info,
        **opensm,
        "interfaces": ipoib_interfaces,
    }

    evidence = {
        "evidence_version": "1.0",
        "node_id": node_id,
        "build_id": build_id,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "matrix_dimensions": matrix,
        "test_results": test_results,
        "notes": [
            "SoftRoCE evidence is NOT valid as IPoIB release evidence",
            "Only configurations present in this matrix are release-claimed",
        ],
    }

    evidence_file = os.path.join(
        output_dir, f"evidence-{node_id}.json",
    )
    with open(evidence_file, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=2)

    module.exit_json(
        changed=False,
        evidence=evidence,
        evidence_file=evidence_file,
        matrix_dimensions=matrix,
    )


def main() -> None:
    """Module entry point."""
    run_module()


if __name__ == "__main__":
    main()
