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
"""Render IPoIB IPv6 configuration artifacts for NM, SMD, BSS, and /etc/hosts.

This module implements Story 2 (ER-ORCH-005-nm-config-publication):
- Renders nmcli commands for each node/interface (dual-stack, IPv6-only, IPv4-only)
- Generates cloud-init user-data (write_files + runcmd) for BSS delivery
- Renders SMD component/interface payloads for hardware state registration
- Renders managed /etc/hosts block from the complete active snapshot
- Computes config hash for idempotent reapplication detection

Consumes the normalized_nodes output from validate_ib_ipv6_allocation.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.orchestrator_validation.renderers import (
    nm_renderer,
)

DOCUMENTATION = r'''
---
module: render_ib_ipv6_config
short_description: Render IPoIB IPv6 configuration artifacts
version_added: "2.3.0"
description:
  - Renders nmcli commands for NM profile creation per interface.
  - Generates cloud-init user-data scripts for BSS delivery.
  - Renders SMD component/interface payloads.
  - Renders managed /etc/hosts block.
  - Computes config hashes for idempotent reapplication.
options:
  normalized_nodes:
    description: >
      Per-node, per-interface allocation map produced by
      validate_ib_ipv6_allocation.
    required: true
    type: dict
  output_dir:
    description: >
      Directory to write rendered artifacts (cloud-init scripts,
      SMD payloads, hosts block).
    required: true
    type: str
  previous_hashes:
    description: >
      Dict of node_id → config_hash from the previous run.
      Used for idempotent reapplication detection.
    required: false
    type: dict
    default: {}
  log_dir:
    description: Directory for the render log.
    required: false
    type: str
    default: ""
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Render IPoIB IPv6 configuration
  omnia.orchestrator.render_ib_ipv6_config:
    normalized_nodes: "{{ ib_ipv6_validation.normalized_nodes }}"
    output_dir: "{{ orchestrator_output_dir }}/ib_ipv6"
    previous_hashes: "{{ ib_ipv6_previous_hashes | default({}) }}"
    log_dir: "{{ omnia_data_path }}/log/core/playbooks"
  register: ib_ipv6_render

- name: Write managed hosts block to OIM
  ansible.builtin.blockinfile:
    path: /etc/hosts
    block: "{{ ib_ipv6_render.hosts_block_content }}"
    marker: "# {mark} Omnia IPoIB managed block"
  when: ib_ipv6_render.hosts_block_content | length > 0
'''

RETURN = r'''
node_results:
  description: Per-node render results with NM commands, cloud-init, SMD payloads.
  returned: always
  type: dict
cloud_init_scripts:
  description: Dict of node_id to cloud-init script paths written to output_dir.
  returned: always
  type: dict
smd_payloads:
  description: Dict of node_id to SMD component payload paths written to output_dir.
  returned: always
  type: dict
hosts_block_content:
  description: The rendered managed /etc/hosts block content.
  returned: always
  type: str
hosts_block_file:
  description: Path to the written hosts block file.
  returned: always
  type: str
config_hashes:
  description: Dict of node_id to config hash for idempotent tracking.
  returned: always
  type: dict
nodes_needing_update:
  description: List of node IDs whose config changed since previous run.
  returned: always
  type: list
  elements: str
nodes_skipped:
  description: List of node IDs skipped (unchanged config).
  returned: always
  type: list
  elements: str
errors:
  description: Render errors (e.g., routed input rejections).
  returned: always
  type: list
  elements: str
log_file:
  description: Absolute path to the render log.
  returned: always
  type: str
'''


def _create_logger(log_dir: str) -> tuple[logging.Logger, str]:
    """Create a render logger."""
    os.makedirs(log_dir, mode=0o750, exist_ok=True)
    log_file = os.path.join(log_dir, "ib_ipv6_render.log")
    handler = logging.FileHandler(log_file, mode="w")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    logger = logging.getLogger("ib_ipv6_render")
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
            "normalized_nodes": {"type": "dict", "required": True},
            "output_dir": {"type": "str", "required": True},
            "previous_hashes": {
                "type": "dict",
                "required": False,
                "default": {},
            },
            "log_dir": {"type": "str", "required": False, "default": ""},
        },
        supports_check_mode=True,
    )
    normalized_nodes = module.params["normalized_nodes"]
    output_dir = os.path.realpath(module.params["output_dir"])
    previous_hashes = module.params["previous_hashes"]
    configured_log_dir = module.params["log_dir"] or os.path.join(
        os.getenv("OMNIA_DATA_PATH", "/opt/omnia"),
        "log", "core", "playbooks",
    )
    logger, log_file = _create_logger(os.path.realpath(configured_log_dir))

    os.makedirs(output_dir, mode=0o755, exist_ok=True)
    scripts_dir = os.path.join(output_dir, "scripts")
    smd_dir = os.path.join(output_dir, "smd")
    os.makedirs(scripts_dir, mode=0o755, exist_ok=True)
    os.makedirs(smd_dir, mode=0o755, exist_ok=True)

    node_results: dict[str, Any] = {}
    cloud_init_scripts: dict[str, str] = {}
    smd_payloads: dict[str, str] = {}
    config_hashes: dict[str, str] = {}
    nodes_needing_update: list[str] = []
    nodes_skipped: list[str] = []
    all_errors: list[str] = []

    for node_id in sorted(normalized_nodes.keys()):
        interfaces = normalized_nodes[node_id]
        result = nm_renderer.render_node_full(node_id, interfaces, logger)
        node_results[node_id] = result

        if result["errors"]:
            all_errors.extend(result["errors"])
            continue

        config_hashes[node_id] = result["config_hash"]

        # Idempotent check
        if not nm_renderer.is_reapplication_needed(
            result["config_hash"], previous_hashes.get(node_id)
        ):
            nodes_skipped.append(node_id)
            logger.info(
                "[IB-IPv6] Node %s: config unchanged, skipping", node_id,
            )
            continue

        nodes_needing_update.append(node_id)

        # Write cloud-init script
        ci_data = result["cloud_init"]
        if ci_data.get("write_files"):
            script_path = os.path.join(
                scripts_dir, f"configure-ipoib-{node_id}.sh",
            )
            with open(script_path, "w", encoding="utf-8") as fh:
                fh.write(ci_data["write_files"][0]["content"])
            os.chmod(script_path, 0o755)
            cloud_init_scripts[node_id] = script_path

        # Write SMD payload
        smd_path = os.path.join(smd_dir, f"smd-{node_id}.json")
        with open(smd_path, "w", encoding="utf-8") as fh:
            json.dump(result["smd_component"], fh, indent=2)
        smd_payloads[node_id] = smd_path

    # Render managed hosts block from the complete active snapshot
    hosts_block = nm_renderer.render_managed_hosts_block(
        normalized_nodes, logger,
    )
    hosts_file = os.path.join(output_dir, "managed_hosts_block.txt")
    with open(hosts_file, "w", encoding="utf-8") as fh:
        fh.write(hosts_block)

    # Write config hashes for next run
    hashes_file = os.path.join(output_dir, "config_hashes.json")
    with open(hashes_file, "w", encoding="utf-8") as fh:
        json.dump(config_hashes, fh, indent=2)

    logger.info(
        "[IB-IPv6] Render complete: %d nodes updated, %d skipped, %d errors",
        len(nodes_needing_update), len(nodes_skipped), len(all_errors),
    )

    module.exit_json(
        changed=len(nodes_needing_update) > 0,
        node_results=node_results,
        cloud_init_scripts=cloud_init_scripts,
        smd_payloads=smd_payloads,
        hosts_block_content=hosts_block,
        hosts_block_file=hosts_file,
        config_hashes=config_hashes,
        nodes_needing_update=nodes_needing_update,
        nodes_skipped=nodes_skipped,
        errors=all_errors,
        log_file=log_file,
    )


def main() -> None:
    """Module entry point."""
    run_module()


if __name__ == "__main__":
    main()
