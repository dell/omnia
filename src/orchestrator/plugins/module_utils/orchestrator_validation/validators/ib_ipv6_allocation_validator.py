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
"""IPoIB IPv6 allocation import, validation, normalization, and atomicity.

Implements ER-ORCH-005 FR-1 (mode/prefix validation) and FR-2 (versioned
per-interface allocation contract). This module is the foundation layer
consumed by downstream NM rendering, SMD publication, and diagnostics.
"""

from __future__ import annotations

import ipaddress
import json
import os
from collections import defaultdict
from logging import Logger
from pathlib import Path
from typing import Any

SUPPORTED_SCHEMA_VERSION = "1.0"
VALID_LIFECYCLE_STATES = {"active", "reserved", "retired"}
CONFIGURABLE_LIFECYCLE_STATES = {"active"}
VALID_ADDRESS_FAMILIES = {"ipv4", "ipv6"}
VALID_IB_MODES = {"datagram", "connected"}


# ---------------------------------------------------------------------------
# IPv6 normalization
# ---------------------------------------------------------------------------

def normalize_ipv6(address: str) -> str | None:
    """Return the canonical compressed form of an IPv6 address, or None.

    Handles textual equivalence: ``fd00:1b::1`` and
    ``fd00:1b:0000:0000:0000:0000:0000:0001`` are treated as the same address.

    Args:
        address: IPv6 address string in any valid textual form.

    Returns:
        Compressed canonical form, or ``None`` for invalid input.
    """
    try:
        return str(ipaddress.IPv6Address(address))
    except (ValueError, TypeError):
        return None


def normalize_address(address: str, family: str) -> str | None:
    """Return canonical form for an address of the given family.

    Args:
        address: Address string.
        family: ``'ipv4'`` or ``'ipv6'``.

    Returns:
        Canonical form, or ``None`` for invalid input.
    """
    try:
        if family == "ipv6":
            return str(ipaddress.IPv6Address(address))
        return str(ipaddress.IPv4Address(address))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------

def _load_schema() -> dict[str, Any]:
    """Load the allocation export JSON Schema from the co-located file."""
    schema_path = (
        Path(__file__).resolve().parent.parent
        / "schema"
        / "ib_ipv6_allocation.json"
    )
    with open(schema_path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Allocation file loading
# ---------------------------------------------------------------------------

def load_allocation_file(path: str) -> tuple[dict[str, Any] | None, str | None]:
    """Load and parse a JSON allocation export file.

    Args:
        path: Filesystem path to the allocation export JSON.

    Returns:
        ``(parsed_data, None)`` on success, or ``(None, error_message)`` on
        failure.
    """
    if not os.path.isfile(path):
        return None, f"Allocation file not found: {path}"
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        return None, f"Failed to parse allocation file {path}: {exc}"
    if not isinstance(data, dict):
        return None, f"Allocation file {path}: expected JSON object at root."
    return data, None


# ---------------------------------------------------------------------------
# Schema validation (L1)
# ---------------------------------------------------------------------------

def validate_schema(
    data: dict[str, Any],
    logger: Logger | None = None,
) -> list[str]:
    """Validate allocation export against the JSON Schema (L1).

    Args:
        data: Parsed allocation export JSON.
        logger: Optional validation logger.

    Returns:
        List of schema validation error messages.
    """
    from jsonschema import FormatChecker
    from jsonschema.exceptions import SchemaError
    from jsonschema.validators import validator_for

    errors: list[str] = []
    try:
        schema_def = _load_schema()
    except (OSError, json.JSONDecodeError) as exc:
        msg = f"ib_ipv6_allocation: failed to load schema: {exc}"
        errors.append(msg)
        if logger:
            logger.error(msg)
        return errors

    try:
        validator_class = validator_for(schema_def)
        validator_class.check_schema(schema_def)
    except SchemaError as exc:
        msg = f"ib_ipv6_allocation: invalid schema: {exc.message}"
        errors.append(msg)
        if logger:
            logger.error(msg)
        return errors

    validator = validator_class(schema_def, format_checker=FormatChecker())
    for error in sorted(
        validator.iter_errors(data),
        key=lambda e: list(e.absolute_path),
    ):
        path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        msg = f"ib_ipv6_allocation.{path}: {error.message}"
        errors.append(msg)
        if logger:
            logger.error(msg)
    return errors


# ---------------------------------------------------------------------------
# Semantic validation (L2)
# ---------------------------------------------------------------------------

def _validate_version(data: dict[str, Any]) -> list[str]:
    """Validate schema version compatibility."""
    version = data.get("schema_version", "")
    if version != SUPPORTED_SCHEMA_VERSION:
        return [
            f"ib_ipv6_allocation: unsupported schema_version '{version}', "
            f"expected '{SUPPORTED_SCHEMA_VERSION}'."
        ]
    return []


def _validate_address(record: dict[str, Any], index: int) -> list[str]:
    """Validate a single allocation record's address field."""
    errors: list[str] = []
    address = record.get("address", "")
    family = record.get("address_family", "")
    alloc_id = record.get("allocation_id", f"[{index}]")

    canonical = normalize_address(address, family)
    if canonical is None:
        errors.append(
            f"allocation {alloc_id}: address '{address}' is not a valid "
            f"{family} address."
        )
    return errors


def _validate_prefix(record: dict[str, Any], index: int) -> list[str]:
    """Validate approved_prefix if present."""
    errors: list[str] = []
    prefix = record.get("approved_prefix")
    if prefix is None:
        return errors

    alloc_id = record.get("allocation_id", f"[{index}]")
    family = record.get("address_family", "")

    try:
        network = ipaddress.ip_network(prefix, strict=False)
        if family == "ipv6" and not isinstance(network, ipaddress.IPv6Network):
            errors.append(
                f"allocation {alloc_id}: approved_prefix '{prefix}' is not "
                f"an IPv6 network."
            )
        elif family == "ipv4" and not isinstance(network, ipaddress.IPv4Network):
            errors.append(
                f"allocation {alloc_id}: approved_prefix '{prefix}' is not "
                f"an IPv4 network."
            )
    except ValueError:
        errors.append(
            f"allocation {alloc_id}: approved_prefix '{prefix}' is malformed."
        )
    return errors


def _validate_address_in_prefix(record: dict[str, Any], index: int) -> list[str]:
    """Validate the address falls within its approved prefix."""
    errors: list[str] = []
    prefix = record.get("approved_prefix")
    address = record.get("address", "")
    if prefix is None:
        return errors

    alloc_id = record.get("allocation_id", f"[{index}]")
    try:
        network = ipaddress.ip_network(prefix, strict=False)
        addr = ipaddress.ip_address(address)
        if addr not in network:
            errors.append(
                f"allocation {alloc_id}: address '{address}' is outside "
                f"approved_prefix '{prefix}'."
            )
    except ValueError:
        pass  # Already caught by _validate_address or _validate_prefix
    return errors


def _detect_duplicates(allocations: list[dict[str, Any]]) -> list[str]:
    """Detect duplicate addresses within the same interface scope.

    IPv6 duplicates are detected using normalized (canonical compressed)
    comparison, so ``fd00:1b::1`` and ``fd00:1b:0:0:0:0:0:1`` are treated
    as duplicates.
    """
    errors: list[str] = []
    seen: dict[str, str] = {}

    for record in allocations:
        address = record.get("address", "")
        family = record.get("address_family", "")
        alloc_id = record.get("allocation_id", "unknown")

        canonical = normalize_address(address, family)
        if canonical is None:
            continue

        key = f"{family}:{canonical}"
        if key in seen:
            errors.append(
                f"allocation {alloc_id}: duplicate address '{address}' "
                f"(canonical: {canonical}), first seen in allocation "
                f"'{seen[key]}'."
            )
        else:
            seen[key] = alloc_id

    return errors


def _validate_lifecycle(allocations: list[dict[str, Any]]) -> list[str]:
    """Flag non-active allocations that should not be configured."""
    errors: list[str] = []
    for record in allocations:
        state = record.get("lifecycle_state", "")
        alloc_id = record.get("allocation_id", "unknown")
        if state not in VALID_LIFECYCLE_STATES:
            errors.append(
                f"allocation {alloc_id}: lifecycle_state '{state}' is not "
                f"one of {sorted(VALID_LIFECYCLE_STATES)}."
            )
    return errors


def validate_semantic(
    data: dict[str, Any],
    logger: Logger | None = None,
) -> list[str]:
    """Run L2 semantic validation on the allocation export.

    Checks: schema version, per-record address validity, approved-prefix
    validity, address-in-prefix containment, duplicate detection (with
    IPv6 normalization), and lifecycle state.

    Args:
        data: Parsed allocation export JSON (already L1-valid).
        logger: Optional validation logger.

    Returns:
        List of semantic validation error messages.
    """
    errors: list[str] = []
    errors.extend(_validate_version(data))

    allocations = data.get("allocations", [])
    for index, record in enumerate(allocations):
        errors.extend(_validate_address(record, index))
        errors.extend(_validate_prefix(record, index))
        errors.extend(_validate_address_in_prefix(record, index))

    errors.extend(_detect_duplicates(allocations))
    errors.extend(_validate_lifecycle(allocations))

    for msg_text in errors:
        if logger:
            logger.error(msg_text)
    return errors


# ---------------------------------------------------------------------------
# Allocation Normalizer — per-node, per-interface grouping
# ---------------------------------------------------------------------------

def filter_active(
    allocations: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Partition allocations into active and non-active sets.

    Args:
        allocations: All allocation records.

    Returns:
        ``(active_records, excluded_records)`` where excluded are reserved
        or retired.
    """
    active: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for record in allocations:
        if record.get("lifecycle_state") in CONFIGURABLE_LIFECYCLE_STATES:
            active.append(record)
        else:
            excluded.append(record)
    return active, excluded


def normalize_per_node(
    active_allocations: list[dict[str, Any]],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Group active allocations by node_id and interface_id.

    Args:
        active_allocations: Only ``lifecycle_state == 'active'`` records.

    Returns:
        ``{node_id: {interface_id: [allocation_records]}}``
    """
    result: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for record in active_allocations:
        node = record.get("node_id", "unknown")
        iface = record.get("interface_id", "unknown")
        result[node][iface].append(record)
    return dict(result)


# ---------------------------------------------------------------------------
# Legacy Adapter — flat IB_IPV4 compatibility projection
# ---------------------------------------------------------------------------

def legacy_ib_ip_projection(
    node_interfaces: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    """Project a single-interface node into a flat IB_IPV4-compatible record.

    This adapter supports backward compatibility with existing consumers
    that expect a single IPv4 ``IB_IPV4`` field per node. Returns ``None``
    for multi-interface nodes (they use the full normalized model).

    Args:
        node_interfaces: ``{interface_id: [allocation_records]}`` for one
            node.

    Returns:
        ``{"IB_IPV4": "<ipv4_address>"}`` dict for single-interface nodes
        with an IPv4 allocation, or ``None``.
    """
    if len(node_interfaces) != 1:
        return None

    iface_id = next(iter(node_interfaces))
    records = node_interfaces[iface_id]
    ipv4_records = [
        r for r in records if r.get("address_family") == "ipv4"
    ]
    if len(ipv4_records) != 1:
        return None

    return {"IB_IPV4": ipv4_records[0].get("address", "")}


# ---------------------------------------------------------------------------
# IB network mode detection
# ---------------------------------------------------------------------------

def detect_ib_mode(
    node_interfaces: dict[str, list[dict[str, Any]]],
) -> str:
    """Determine the IB address-family mode for a node.

    Args:
        node_interfaces: ``{interface_id: [allocation_records]}`` for one
            node.

    Returns:
        ``'ipv4-only'``, ``'ipv6-only'``, or ``'dual-stack'``.
    """
    has_ipv4 = False
    has_ipv6 = False
    for records in node_interfaces.values():
        for record in records:
            family = record.get("address_family", "")
            if family == "ipv4":
                has_ipv4 = True
            elif family == "ipv6":
                has_ipv6 = True

    if has_ipv4 and has_ipv6:
        return "dual-stack"
    if has_ipv6:
        return "ipv6-only"
    return "ipv4-only"


# ---------------------------------------------------------------------------
# Node-scoped preflight with atomicity
# ---------------------------------------------------------------------------

def validate_node(
    node_id: str,
    interfaces: dict[str, list[dict[str, Any]]],
) -> list[str]:
    """Run per-node preflight validation.

    A failed node produces no partial artifacts — all errors are collected
    and the node is rejected as a whole.

    Args:
        node_id: Node identifier.
        interfaces: ``{interface_id: [allocation_records]}``.

    Returns:
        Error messages for this node. Empty list means the node is valid.
    """
    errors: list[str] = []
    for iface_id, records in interfaces.items():
        for record in records:
            address = record.get("address", "")
            family = record.get("address_family", "")
            alloc_id = record.get("allocation_id", "unknown")

            if normalize_address(address, family) is None:
                errors.append(
                    f"node {node_id}, interface {iface_id}, "
                    f"allocation {alloc_id}: invalid {family} address "
                    f"'{address}'."
                )

            prefix = record.get("approved_prefix")
            if prefix:
                try:
                    network = ipaddress.ip_network(prefix, strict=False)
                    addr = ipaddress.ip_address(address)
                    if addr not in network:
                        errors.append(
                            f"node {node_id}, interface {iface_id}, "
                            f"allocation {alloc_id}: address '{address}' "
                            f"outside approved_prefix '{prefix}'."
                        )
                except ValueError:
                    errors.append(
                        f"node {node_id}, interface {iface_id}, "
                        f"allocation {alloc_id}: malformed "
                        f"approved_prefix '{prefix}'."
                    )
    return errors


def preflight_validate(
    data: dict[str, Any],
    logger: Logger | None = None,
) -> tuple[
    dict[str, dict[str, list[dict[str, Any]]]],
    dict[str, list[str]],
]:
    """Run the full preflight pipeline: filter, normalize, validate per-node.

    Node-scoped atomicity: a node with any validation error produces no
    artifacts. Valid nodes proceed independently.

    Args:
        data: Parsed and schema-valid allocation export.
        logger: Optional validation logger.

    Returns:
        ``(valid_nodes, failed_nodes)`` where ``valid_nodes`` maps
        ``node_id -> {interface_id -> [records]}`` and ``failed_nodes``
        maps ``node_id -> [error_messages]``.
    """
    allocations = data.get("allocations", [])
    active, excluded = filter_active(allocations)

    if excluded and logger:
        for record in excluded:
            logger.info(
                "Excluded non-active allocation %s (state: %s)",
                record.get("allocation_id", "?"),
                record.get("lifecycle_state", "?"),
            )

    per_node = normalize_per_node(active)

    valid_nodes: dict[str, dict[str, list[dict[str, Any]]]] = {}
    failed_nodes: dict[str, list[str]] = {}

    for node_id, interfaces in per_node.items():
        node_errors = validate_node(node_id, interfaces)
        if node_errors:
            failed_nodes[node_id] = node_errors
            if logger:
                for err in node_errors:
                    logger.error(err)
        else:
            valid_nodes[node_id] = interfaces

    return valid_nodes, failed_nodes
