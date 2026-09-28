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
"""Validate IPoIB IPv6 allocation export and produce normalized node set.

This module implements Story 1 (ER-ORCH-005-allocation-import-validation):
- Loads the allocation export JSON from the configured path
- Runs L1 schema validation (16-field versioned schema)
- Runs L2 semantic validation (address validity, prefix containment, duplicates)
- Normalizes per-node/per-interface and filters by lifecycle
- Detects IB mode (dual-stack / ipv6-only / ipv4-only)
- Produces a legacy IB_IPV4 adapter projection for backward compatibility
- Enforces node-scoped atomicity (failed node → no artifacts)

The normalized output is consumed by the render_ib_ipv6_config module.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.orchestrator_validation.validators import (
    ib_ipv6_allocation_validator as validator,
)

DOCUMENTATION = r'''
---
module: validate_ib_ipv6_allocation
short_description: Validate IPoIB IPv6 allocation export
version_added: "2.3.0"
description:
  - Loads and validates the IPoIB IPv6 allocation export JSON file.
  - Performs JSON Schema L1 and cross-field L2 semantic validation.
  - Normalizes allocations per-node/per-interface for downstream rendering.
  - Detects IB mode and produces legacy IB_IPV4 adapter output.
  - Enforces node-scoped atomicity — a failed node produces no artifacts.
options:
  allocation_file:
    description: >
      Absolute path to the IPoIB IPv6 allocation export JSON file.
      This file is produced by the IPAM or static allocation tool.
    required: true
    type: str
  approved_prefixes:
    description: >
      List of approved IPv6 prefix strings (CIDR notation).
      Only addresses within these prefixes are accepted.
    required: false
    type: list
    elements: str
    default: []
  log_dir:
    description: Directory where the validation log is written.
    required: false
    type: str
    default: ""
author:
  - Dell Omnia Team
'''

EXAMPLES = r'''
- name: Validate IPoIB IPv6 allocation export
  omnia.orchestrator.validate_ib_ipv6_allocation:
    allocation_file: "{{ orchestrator_data_path }}/input/ib_ipv6_allocation.json"
    approved_prefixes: "{{ network_spec.ib_ipv6_approved_prefixes | default([]) }}"
    log_dir: "{{ omnia_data_path }}/log/core/playbooks"
  register: ib_ipv6_validation

- name: Fail if allocation validation failed
  ansible.builtin.fail:
    msg: "IPoIB IPv6 allocation validation failed: {{ ib_ipv6_validation.errors }}"
  when: ib_ipv6_validation.validation_failed
'''

RETURN = r'''
validation_failed:
  description: Whether any validation error was found.
  returned: always
  type: bool
errors:
  description: Validation error messages.
  returned: always
  type: list
  elements: str
normalized_nodes:
  description: >
    Per-node, per-interface allocation map.  Keys are node IDs; values are
    dicts mapping interface IDs to lists of allocation records.
  returned: success
  type: dict
ib_mode:
  description: >
    Detected IB addressing mode: dual-stack, ipv6-only, or ipv4-only.
  returned: success
  type: str
legacy_ib_ip:
  description: >
    Legacy flat IB_IPV4 projection for backward-compatible single-interface
    IPv4 nodes.
  returned: success
  type: dict
snapshot_id:
  description: Allocation export snapshot identifier.
  returned: success
  type: str
total_allocations:
  description: Total number of allocation records processed.
  returned: always
  type: int
active_allocations:
  description: Number of active allocation records after lifecycle filtering.
  returned: success
  type: int
log_file:
  description: Absolute path to the validation log.
  returned: always
  type: str
'''


def _create_logger(log_dir: str) -> tuple[logging.Logger, str]:
    """Create a validation logger."""
    os.makedirs(log_dir, mode=0o750, exist_ok=True)
    log_file = os.path.join(log_dir, "ib_ipv6_allocation_validation.log")
    handler = logging.FileHandler(log_file, mode="w")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    logger = logging.getLogger("ib_ipv6_allocation_validation")
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
            "allocation_file": {"type": "str", "required": True},
            "approved_prefixes": {
                "type": "list",
                "elements": "str",
                "required": False,
                "default": [],
            },
            "log_dir": {"type": "str", "required": False, "default": ""},
        },
        supports_check_mode=True,
    )
    allocation_file = os.path.realpath(module.params["allocation_file"])
    configured_log_dir = module.params["log_dir"] or os.path.join(
        os.getenv("OMNIA_DATA_PATH", "/opt/omnia"),
        "log", "core", "playbooks",
    )
    log_dir = os.path.realpath(configured_log_dir)
    logger, log_file = _create_logger(log_dir)

    # --- Load allocation file ---
    if not os.path.isfile(allocation_file):
        module.fail_json(
            msg=f"Allocation file not found: {allocation_file}",
            validation_failed=True,
            errors=[f"File not found: {allocation_file}"],
            log_file=log_file,
            total_allocations=0,
        )
        return

    try:
        with open(allocation_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        module.fail_json(
            msg=f"Failed to parse allocation file: {exc}",
            validation_failed=True,
            errors=[f"Parse error: {exc}"],
            log_file=log_file,
            total_allocations=0,
        )
        return

    total_allocations = len(data.get("allocations", []))
    logger.info(
        "[IB-IPv6] Loaded %d allocation records from %s",
        total_allocations, allocation_file,
    )

    # --- L1 schema validation ---
    schema_errors = validator.validate_schema(data, logger)
    if schema_errors:
        module.exit_json(
            changed=False,
            validation_failed=True,
            errors=schema_errors,
            normalized_nodes={},
            ib_mode="unknown",
            legacy_ib_ip={},
            snapshot_id=data.get("snapshot_id", ""),
            total_allocations=total_allocations,
            active_allocations=0,
            log_file=log_file,
        )
        return

    # --- L2 semantic validation ---
    semantic_errors = validator.validate_semantic(data, logger)
    if semantic_errors:
        module.exit_json(
            changed=False,
            validation_failed=True,
            errors=semantic_errors,
            normalized_nodes={},
            ib_mode="unknown",
            legacy_ib_ip={},
            snapshot_id=data.get("snapshot_id", ""),
            total_allocations=total_allocations,
            active_allocations=0,
            log_file=log_file,
        )
        return

    # --- Preflight: normalize, filter, group, detect mode ---
    normalized_nodes, rejected_nodes = validator.preflight_validate(
        data, logger
    )
    active_count = sum(
        len(records)
        for ifaces in normalized_nodes.values()
        for records in ifaces.values()
    )

    ib_mode = validator.detect_ib_mode(data)
    legacy_ib_ip = validator.legacy_ib_ip_adapter(normalized_nodes)

    rejection_errors = []
    for node_id, reasons in rejected_nodes.items():
        for reason in reasons:
            rejection_errors.append(
                f"[IB-IPv6] Node {node_id} rejected: {reason}"
            )

    logger.info(
        "[IB-IPv6] Validation complete: %d active allocations across %d nodes, "
        "mode=%s, %d rejections",
        active_count, len(normalized_nodes), ib_mode, len(rejection_errors),
    )

    module.exit_json(
        changed=False,
        validation_failed=False,
        errors=rejection_errors,
        normalized_nodes=normalized_nodes,
        ib_mode=ib_mode,
        legacy_ib_ip=legacy_ib_ip,
        snapshot_id=data.get("snapshot_id", ""),
        total_allocations=total_allocations,
        active_allocations=active_count,
        log_file=log_file,
    )


def main() -> None:
    """Module entry point."""
    run_module()


if __name__ == "__main__":
    main()
