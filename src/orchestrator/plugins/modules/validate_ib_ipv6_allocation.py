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
"""Validate IPoIB IPv6 allocations and produce normalized node set.

This module implements Story 1 (ER-ORCH-005-allocation-import-validation):
- Loads IPoIB allocations from the PXE mapping file (primary) or JSON (legacy)
- Validates IB columns: IB_NIC_NAME, IB_IPV4/IB_IPV6 (or legacy IB_IP)
- Validates address validity, CIDR prefix length, duplicates, prohibited classes
- Normalizes per-node/per-interface for downstream rendering
- Detects IB mode (dual-stack / ipv6-only / ipv4-only)
- Produces a legacy IB_IPV4 adapter projection for backward compatibility
- Enforces node-scoped atomicity (failed node -> no artifacts)

The PXE mapping file (pxe_mapping_file.csv) is the sole ingestion interface
for IPoIB allocations per ER-ORCH-005 / BR-34869 v6.1.

The normalized output is consumed by the render_ib_ipv6_config module.
"""

from __future__ import annotations

import csv
import ipaddress
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
short_description: Validate IPoIB IPv6 allocations from PXE mapping file
version_added: "2.3.0"
description:
  - Loads and validates IPoIB IPv6 allocations from the PXE mapping file (primary)
    or a legacy JSON allocation export file.
  - Validates IB columns (IB_NIC_NAME, IB_IPV4/IB_IPV6), address validity,
    CIDR prefix length, duplicates, and prohibited address classes.
  - Normalizes allocations per-node/per-interface for downstream rendering.
  - Detects IB mode and produces legacy IB_IPV4 adapter output.
  - Enforces node-scoped atomicity — a failed node produces no artifacts.
options:
  pxe_mapping_file:
    description: >
      Absolute path to the PXE mapping CSV file (pxe_mapping_file.csv).
      This is the sole ingestion interface for IPoIB allocations per
      ER-ORCH-005 / BR-34869 v6.1. Mandatory IB columns: SERVICE_TAG or
      HOSTNAME, IB_NIC_NAME, IB_IPV4/IB_IPV6 (or legacy IB_IP).
    required: false
    type: str
    default: ""
  allocation_file:
    description: >
      (Legacy) Absolute path to the IPoIB IPv6 allocation export JSON file.
      Deprecated — use pxe_mapping_file instead.
    required: false
    type: str
    default: ""
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
- name: Validate IPoIB IPv6 allocations from PXE mapping file
  omnia.orchestrator.validate_ib_ipv6_allocation:
    pxe_mapping_file: "{{ pxe_mapping_file }}"
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


def _parse_pxe_mapping_ib_rows(
    pxe_file: str, logger: logging.Logger
) -> tuple[list[dict[str, str]], list[str]]:
    """Parse IB allocation rows from a PXE mapping CSV file.

    Returns (ib_rows, errors) where each ib_row has keys:
    HOSTNAME, IB_NIC_NAME, IB_IPV4, IB_IPV6.
    """
    errors: list[str] = []
    ib_rows: list[dict[str, str]] = []
    try:
        with open(pxe_file, "r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                errors.append("PXE mapping file is empty or has no header")
                return ib_rows, errors

            headers = list(reader.fieldnames)
            # Detect legacy IB_IP vs canonical IB_IPV4/IB_IPV6
            is_legacy = "IB_IP" in headers and "IB_IPV4" not in headers

            for row_num, row in enumerate(reader, start=2):
                hostname = row.get("HOSTNAME", "").strip()
                nic_name = row.get("IB_NIC_NAME", "").strip()

                # Skip rows without IB data
                if not nic_name:
                    continue

                if is_legacy:
                    ib_ip = row.get("IB_IP", "").strip()
                    # Detect address family from the value
                    ib_ipv4, ib_ipv6 = "", ""
                    if ib_ip:
                        try:
                            addr = ipaddress.ip_address(ib_ip.split("/")[0])
                            if addr.version == 4:
                                ib_ipv4 = ib_ip
                            else:
                                ib_ipv6 = ib_ip
                        except ValueError:
                            errors.append(
                                f"Row {row_num}: invalid IB_IP '{ib_ip}'"
                            )
                            continue
                else:
                    ib_ipv4 = row.get("IB_IPV4", "").strip()
                    ib_ipv6 = row.get("IB_IPV6", "").strip()

                if not hostname:
                    errors.append(
                        f"Row {row_num}: missing HOSTNAME for IB_NIC_NAME "
                        f"'{nic_name}'"
                    )
                    continue

                if not ib_ipv4 and not ib_ipv6:
                    errors.append(
                        f"Row {row_num}: IB_NIC_NAME '{nic_name}' has no "
                        f"IB_IPV4 or IB_IPV6 address"
                    )
                    continue

                ib_rows.append({
                    "HOSTNAME": hostname,
                    "SERVICE_TAG": row.get("SERVICE_TAG", "").strip(),
                    "IB_NIC_NAME": nic_name,
                    "IB_IPV4": ib_ipv4,
                    "IB_IPV6": ib_ipv6,
                })

    except (OSError, csv.Error, UnicodeError) as exc:
        errors.append(f"Failed to parse PXE mapping file: {exc}")

    logger.info(
        "[IB-IPv6] Parsed %d IB allocation rows from PXE mapping %s",
        len(ib_rows), pxe_file,
    )
    return ib_rows, errors


def _pxe_rows_to_normalized(
    ib_rows: list[dict[str, str]],
    approved_prefixes: list[str],
    logger: logging.Logger,
) -> tuple[dict[str, Any], list[str], str]:
    """Convert PXE mapping IB rows to normalized_nodes format.

    Returns (normalized_nodes, errors, ib_mode).
    normalized_nodes: {hostname: {interface_id: [allocation_records]}}
    """
    errors: list[str] = []
    normalized: dict[str, dict[str, list[dict[str, Any]]]] = {}
    seen_addresses: dict[str, str] = {}  # address -> hostname for dup check
    has_ipv4 = False
    has_ipv6 = False

    # Parse approved prefix networks for containment checks
    approved_nets = []
    for prefix_str in approved_prefixes:
        try:
            approved_nets.append(ipaddress.ip_network(prefix_str, strict=False))
        except ValueError:
            logger.warning(
                "[IB-IPv6] Invalid approved prefix: %s", prefix_str
            )

    for row in ib_rows:
        hostname = row["HOSTNAME"]
        nic_name = row["IB_NIC_NAME"]

        if hostname not in normalized:
            normalized[hostname] = {}

        records: list[dict[str, Any]] = []

        # Process IPv4 address
        if row["IB_IPV4"]:
            addr_str = row["IB_IPV4"]
            try:
                # Parse address and optional prefix
                if "/" in addr_str:
                    iface = ipaddress.ip_interface(addr_str)
                    addr_val = str(iface.ip)
                    prefix_len = iface.network.prefixlen
                else:
                    addr_val = str(ipaddress.ip_address(addr_str))
                    prefix_len = 24  # default IPv4 prefix

                addr_obj = ipaddress.ip_address(addr_val)

                # Prohibited address class check
                if addr_obj.is_loopback:
                    errors.append(
                        f"Prohibited loopback address {addr_val} for "
                        f"{hostname}/{nic_name}"
                    )
                    continue
                if addr_obj.is_multicast:
                    errors.append(
                        f"Prohibited multicast address {addr_val} for "
                        f"{hostname}/{nic_name}"
                    )
                    continue

                # CIDR prefix length validation (1-32)
                if not 1 <= prefix_len <= 32:
                    errors.append(
                        f"Invalid IPv4 prefix length {prefix_len} for "
                        f"{hostname}/{nic_name} (must be 1-32)"
                    )
                    continue

                # Duplicate check
                canonical = str(addr_obj)
                if canonical in seen_addresses:
                    errors.append(
                        f"Duplicate IPv4 address {canonical}: "
                        f"{hostname} and {seen_addresses[canonical]}"
                    )
                else:
                    seen_addresses[canonical] = hostname
                    records.append({
                        "hostname": hostname,
                        "interface_id": nic_name,
                        "address": addr_val,
                        "prefix_length": prefix_len,
                        "address_family": "ipv4",
                    })
                    has_ipv4 = True
            except ValueError as exc:
                errors.append(
                    f"Invalid IB_IPV4 '{addr_str}' for {hostname}: {exc}"
                )

        # Process IPv6 address
        if row["IB_IPV6"]:
            addr_str = row["IB_IPV6"]
            try:
                if "/" in addr_str:
                    iface = ipaddress.ip_interface(addr_str)
                    addr_val = str(iface.ip)
                    prefix_len = iface.network.prefixlen
                else:
                    addr_val = str(ipaddress.ip_address(addr_str))
                    prefix_len = 64  # default IPv6 prefix

                addr_obj = ipaddress.ip_address(addr_val)

                # Prohibited address class check
                if addr_obj.is_loopback:
                    errors.append(
                        f"Prohibited loopback address {addr_val} for "
                        f"{hostname}/{nic_name}"
                    )
                    continue
                if addr_obj.is_multicast:
                    errors.append(
                        f"Prohibited multicast address {addr_val} for "
                        f"{hostname}/{nic_name}"
                    )
                    continue
                if addr_obj.is_link_local:
                    errors.append(
                        f"Prohibited link-local address {addr_val} for "
                        f"{hostname}/{nic_name}"
                    )
                    continue
                if addr_obj == ipaddress.ip_address("::"):
                    errors.append(
                        f"Prohibited unspecified address for "
                        f"{hostname}/{nic_name}"
                    )
                    continue

                # Prefix containment check
                if approved_nets:
                    in_prefix = any(
                        addr_obj in net for net in approved_nets
                        if net.version == 6
                    )
                    if not in_prefix:
                        errors.append(
                            f"IPv6 address {addr_val} for {hostname}/"
                            f"{nic_name} is not within any approved prefix"
                        )
                        continue

                # CIDR prefix length validation (1-128)
                if not 1 <= prefix_len <= 128:
                    errors.append(
                        f"Invalid IPv6 prefix length {prefix_len} for "
                        f"{hostname}/{nic_name} (must be 1-128)"
                    )
                    continue

                # Duplicate check (canonicalize IPv6)
                canonical = str(ipaddress.ip_address(addr_val))
                if canonical in seen_addresses:
                    errors.append(
                        f"Duplicate IPv6 address {canonical}: "
                        f"{hostname} and {seen_addresses[canonical]}"
                    )
                else:
                    seen_addresses[canonical] = hostname
                    records.append({
                        "hostname": hostname,
                        "interface_id": nic_name,
                        "address": addr_val,
                        "prefix_length": prefix_len,
                        "address_family": "ipv6",
                    })
                    has_ipv6 = True
            except ValueError as exc:
                errors.append(
                    f"Invalid IB_IPV6 '{addr_str}' for {hostname}: {exc}"
                )

        if records:
            normalized[hostname][nic_name] = records

    # Detect IB mode
    if has_ipv4 and has_ipv6:
        ib_mode = "dual-stack"
    elif has_ipv6:
        ib_mode = "ipv6-only"
    elif has_ipv4:
        ib_mode = "ipv4-only"
    else:
        ib_mode = "unknown"

    return normalized, errors, ib_mode


def run_module() -> None:
    """Entry point for the Ansible module."""
    module = AnsibleModule(
        argument_spec={
            "pxe_mapping_file": {
                "type": "str", "required": False, "default": "",
            },
            "allocation_file": {
                "type": "str", "required": False, "default": "",
            },
            "approved_prefixes": {
                "type": "list",
                "elements": "str",
                "required": False,
                "default": [],
            },
            "log_dir": {"type": "str", "required": False, "default": ""},
            "schema_file": {"type": "str", "required": False, "default": ""},
        },
        supports_check_mode=True,
    )
    pxe_mapping_file = module.params["pxe_mapping_file"]
    allocation_file = module.params["allocation_file"]
    approved_prefixes = module.params["approved_prefixes"]
    configured_log_dir = module.params["log_dir"] or os.path.join(
        os.getenv("OMNIA_DATA_PATH", "/opt/omnia"),
        "log", "core", "playbooks",
    )
    log_dir = os.path.realpath(configured_log_dir)
    logger, log_file = _create_logger(log_dir)

    # --- PXE mapping file path (primary) ---
    if pxe_mapping_file:
        pxe_file = os.path.realpath(pxe_mapping_file)
        if not os.path.isfile(pxe_file):
            module.fail_json(
                msg=f"PXE mapping file not found: {pxe_file}",
                validation_failed=True,
                errors=[f"File not found: {pxe_file}"],
                log_file=log_file,
                total_allocations=0,
            )
            return

        # Parse IB rows from PXE mapping
        ib_rows, parse_errors = _parse_pxe_mapping_ib_rows(pxe_file, logger)
        if parse_errors:
            module.exit_json(
                changed=False,
                validation_failed=True,
                errors=parse_errors,
                normalized_nodes={},
                ib_mode="unknown",
                legacy_ib_ip={},
                snapshot_id="",
                total_allocations=0,
                active_allocations=0,
                log_file=log_file,
            )
            return

        if not ib_rows:
            module.exit_json(
                changed=False,
                validation_failed=True,
                errors=[
                    "No IB allocation rows found in PXE mapping file. "
                    "Ensure rows have IB_NIC_NAME and IB_IPV4/IB_IPV6 values."
                ],
                normalized_nodes={},
                ib_mode="unknown",
                legacy_ib_ip={},
                snapshot_id="",
                total_allocations=0,
                active_allocations=0,
                log_file=log_file,
            )
            return

        # Convert PXE rows to normalized format and validate
        normalized_nodes, val_errors, ib_mode = _pxe_rows_to_normalized(
            ib_rows, approved_prefixes, logger
        )

        total_allocations = len(ib_rows)
        active_count = sum(
            len(records)
            for ifaces in normalized_nodes.values()
            for records in ifaces.values()
        )

        # Build legacy IB_IPV4 map
        legacy_ib_ip: dict[str, Any] = {}
        for node_id, node_ifaces in normalized_nodes.items():
            for iface_id, records in node_ifaces.items():
                ipv4_records = [
                    r for r in records if r["address_family"] == "ipv4"
                ]
                if len(node_ifaces) == 1 and len(ipv4_records) == 1:
                    legacy_ib_ip[node_id] = {
                        "IB_IPV4": ipv4_records[0]["address"]
                    }

        logger.info(
            "[IB-IPv6] PXE mapping validation complete: %d IB rows, "
            "%d active allocations across %d nodes, mode=%s, %d errors",
            total_allocations, active_count, len(normalized_nodes),
            ib_mode, len(val_errors),
        )

        module.exit_json(
            changed=False,
            validation_failed=len(val_errors) > 0,
            errors=val_errors,
            normalized_nodes=normalized_nodes if not val_errors else {},
            ib_mode=ib_mode,
            legacy_ib_ip=legacy_ib_ip,
            snapshot_id="",
            total_allocations=total_allocations,
            active_allocations=active_count,
            log_file=log_file,
        )
        return

    # --- Legacy JSON allocation file path ---
    if not allocation_file:
        module.fail_json(
            msg="Either pxe_mapping_file or allocation_file must be provided",
            validation_failed=True,
            errors=["No input file specified"],
            log_file=log_file,
            total_allocations=0,
        )
        return

    allocation_file = os.path.realpath(allocation_file)
    schema_file = module.params["schema_file"]

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
        "[IB-IPv6] Loaded %d allocation records from %s (legacy JSON)",
        total_allocations, allocation_file,
    )

    schema_errors = validator.validate_schema(data, logger, schema_file)
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

    normalized_nodes, rejected_nodes = validator.preflight_validate(
        data, logger
    )
    active_count = sum(
        len(records)
        for ifaces in normalized_nodes.values()
        for records in ifaces.values()
    )

    if normalized_nodes:
        first_node_ifaces = next(iter(normalized_nodes.values()))
        ib_mode = validator.detect_ib_mode(first_node_ifaces)
    else:
        ib_mode = "unknown"

    legacy_ib_ip = {}
    for node_id, node_ifaces in normalized_nodes.items():
        projection = validator.legacy_ib_ip_projection(node_ifaces)
        if projection is not None:
            legacy_ib_ip[node_id] = projection

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
