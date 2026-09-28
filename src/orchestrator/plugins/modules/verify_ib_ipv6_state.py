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
"""Verify IPoIB IPv6 post-configuration state on a target node.

This module implements Story 3 (ER-ORCH-005-diagnostics-failure-states):
- Address-state verification (DAD, tentative, deprecated, dadfailed)
- Autonomous address detection (SLAAC, EUI-64, privacy, MAC/GUID)
- Route verification (no IPoIB default route)
- Peer reachability (on-link IPv6 ping)
- OpenSM non-regression (config/LID/GID/P_Key diff)
- Privacy extension verification (sysctl check)
- Health status reporting (HEALTHY / DEGRADED_IPV6 / FAILED / RECOVERY)

This module runs on the TARGET NODE (not OIM) via delegate_to or direct SSH.
It inspects the live system state and returns structured diagnostics.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.orchestrator_validation.renderers import (
    address_verifier as verifier,
)

DOCUMENTATION = r'''
---
module: verify_ib_ipv6_state
short_description: Verify IPoIB IPv6 post-configuration state
version_added: "2.3.0"
description:
  - Runs post-configuration verification on a target node.
  - Checks address state, autonomous addresses, routes, privacy, peers.
  - Reports structured health status per interface.
  - Compares OpenSM snapshots for non-regression when provided.
options:
  node_id:
    description: Node identifier (xname or hostname).
    required: true
    type: str
  interfaces:
    description: >
      Dict of interface_id to list of allocation records.
      Same structure as one node's entry from normalized_nodes.
    required: true
    type: dict
  peer_addresses:
    description: >
      Dict of interface_id to peer IPv6 address for reachability check.
    required: false
    type: dict
    default: {}
  opensm_before:
    description: >
      OpenSM snapshot dict (config, lid_gid, pkey checksums) captured
      before IPv6 configuration was applied.
    required: false
    type: dict
    default: {}
  opensm_after:
    description: >
      OpenSM snapshot dict captured after IPv6 configuration.
      When both before and after are provided, non-regression is checked.
    required: false
    type: dict
    default: {}
  log_dir:
    description: Directory for the verification log.
    required: false
    type: str
    default: ""
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Verify IPoIB IPv6 state on target node
  omnia.orchestrator.verify_ib_ipv6_state:
    node_id: "{{ inventory_hostname }}"
    interfaces: "{{ hostvars[inventory_hostname]['ib_ipv6_interfaces'] }}"
    peer_addresses: "{{ ib_ipv6_peer_map | default({}) }}"
    opensm_before: "{{ opensm_snapshot_before | default({}) }}"
    opensm_after: "{{ opensm_snapshot_after | default({}) }}"
  register: ib_ipv6_verify

- name: Report degraded nodes
  ansible.builtin.debug:
    msg: >
      Node {{ ib_ipv6_verify.node_id }} interface {{ item.key }}:
      {{ item.value.health.status }} — {{ item.value.health.errors }}
  loop: "{{ ib_ipv6_verify.interface_results | dict2items }}"
  when: item.value.health.status != 'HEALTHY'
'''

RETURN = r'''
node_id:
  description: Node identifier.
  returned: always
  type: str
overall_status:
  description: >
    Worst health status across all interfaces on this node.
  returned: always
  type: str
interface_results:
  description: >
    Per-interface verification results with health, address checks,
    autonomous addresses, route errors, peer status, privacy check.
  returned: always
  type: dict
opensm_result:
  description: OpenSM non-regression result (if snapshots provided).
  returned: when opensm_before and opensm_after are both provided
  type: dict
events:
  description: Structured [IB-IPv6] events generated during verification.
  returned: always
  type: list
  elements: dict
errors:
  description: All errors across all interfaces.
  returned: always
  type: list
  elements: str
log_file:
  description: Absolute path to the verification log.
  returned: always
  type: str
'''

# Health status priority (worst wins)
_STATUS_PRIORITY = {
    "RECOVERY_REQUIRED": 0,
    "FAILED_IB_CONFIGURATION": 1,
    "DEGRADED_IPV6": 2,
    "HEALTHY": 3,
}


def _run_cmd(cmd: str) -> tuple[str, int]:
    """Run a shell command and return (stdout, returncode)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=30,
        )
        return result.stdout, result.returncode
    except (subprocess.TimeoutExpired, OSError):
        return "", 1


def _create_logger(log_dir: str) -> tuple[logging.Logger, str]:
    """Create a verification logger."""
    os.makedirs(log_dir, mode=0o750, exist_ok=True)
    log_file = os.path.join(log_dir, "ib_ipv6_verification.log")
    handler = logging.FileHandler(log_file, mode="w")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    logger = logging.getLogger("ib_ipv6_verification")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        os.chmod(log_file, 0o640)
    except OSError:
        pass
    return logger, log_file


def run_module() -> None:
    """Entry point for the Ansible module."""
    module = AnsibleModule(
        argument_spec={
            "node_id": {"type": "str", "required": True},
            "interfaces": {"type": "dict", "required": True},
            "peer_addresses": {
                "type": "dict", "required": False, "default": {},
            },
            "opensm_before": {
                "type": "dict", "required": False, "default": {},
            },
            "opensm_after": {
                "type": "dict", "required": False, "default": {},
            },
            "log_dir": {"type": "str", "required": False, "default": ""},
        },
        supports_check_mode=True,
    )
    node_id = module.params["node_id"]
    interfaces = module.params["interfaces"]
    peer_addresses = module.params["peer_addresses"]
    opensm_before = module.params["opensm_before"]
    opensm_after = module.params["opensm_after"]
    configured_log_dir = module.params["log_dir"] or os.path.join(
        os.getenv("OMNIA_DATA_PATH", "/opt/omnia"),
        "log", "core", "playbooks",
    )
    logger, log_file = _create_logger(os.path.realpath(configured_log_dir))
    logger.info("[IB-IPv6] Starting verification for node %s", node_id)

    interface_results: dict[str, Any] = {}
    all_errors: list[str] = []
    events: list[dict[str, Any]] = []
    worst_status = "HEALTHY"

    for iface_id in sorted(interfaces.keys()):
        records = interfaces[iface_id]

        # Gather live system state
        ip_addr_output, _ = _run_cmd(f"ip -6 addr show dev {iface_id}")
        ip_route_output, _ = _run_cmd(f"ip -6 route show dev {iface_id}")
        sysctl_output, _ = _run_cmd(
            f"sysctl net.ipv6.conf.{iface_id}.use_tempaddr"
        )

        # Peer reachability
        ping_output = ""
        ping_rc = 1
        peer_addr = peer_addresses.get(iface_id, "")
        if peer_addr:
            ping_cmd = verifier.build_peer_check_command(
                peer_addr, iface_id, count=3, timeout=5,
            )
            ping_output, ping_rc = _run_cmd(ping_cmd)

        # Run full verification pipeline
        result = verifier.verify_interface(
            node_id=node_id,
            interface_id=iface_id,
            records=records,
            ip_addr_output=ip_addr_output,
            ip_route_output=ip_route_output,
            sysctl_output=sysctl_output,
            ping_output=ping_output,
            ping_rc=ping_rc,
            opensm_before=opensm_before if opensm_before else None,
            opensm_after=opensm_after if opensm_after else None,
            logger=logger,
        )
        interface_results[iface_id] = result
        all_errors.extend(result["health"].get("errors", []))

        # Track worst status
        iface_status = result["health"]["status"]
        if isinstance(iface_status, verifier.HealthStatus):
            iface_status = iface_status.value
        if _STATUS_PRIORITY.get(iface_status, 3) < \
                _STATUS_PRIORITY.get(worst_status, 3):
            worst_status = iface_status

        # Generate structured event
        event = verifier.create_event(
            stage="verification_complete",
            result=iface_status,
            node_id=node_id,
            interface_id=iface_id,
            message=f"Health: {iface_status}, "
                    f"errors: {len(result['health'].get('errors', []))}",
        )
        events.append(event)
        verifier.log_event(event, logger)

    # OpenSM non-regression (cluster-level, not per-interface)
    opensm_result = None
    if opensm_before and opensm_after:
        opensm_result = verifier.compare_opensm_snapshots(
            opensm_before, opensm_after, logger,
        )
        if opensm_result["changed"]:
            worst_status = "RECOVERY_REQUIRED"
            all_errors.append(
                f"OpenSM state changed: {opensm_result['diffs']}"
            )

    logger.info(
        "[IB-IPv6] Verification complete for %s: %s (%d errors)",
        node_id, worst_status, len(all_errors),
    )

    module.exit_json(
        changed=False,
        node_id=node_id,
        overall_status=worst_status,
        interface_results=interface_results,
        opensm_result=opensm_result,
        events=events,
        errors=all_errors,
        log_file=log_file,
    )


def main() -> None:
    """Module entry point."""
    run_module()


if __name__ == "__main__":
    main()
