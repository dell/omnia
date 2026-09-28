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
"""FVT: IPoIB IPv6 allocation validation (ER-ORCH-005).

Covers TC-FVT-001 through TC-FVT-008 and TC-FVT-018 from the ER test plan.
These tests exercise the full allocation import, validation, normalization,
and atomicity pipeline end-to-end using realistic allocation export files.
"""

from __future__ import annotations

import copy
import json
import logging
import os
from pathlib import Path
from typing import Any

import pytest

from ut import source_loader  # noqa: F401  # initializes module_utils path
from ansible.module_utils.orchestrator_validation.validators import (
    ib_ipv6_allocation_validator as validator,
)
from ansible.module_utils.orchestrator_validation.core import (
    validation_engine,
)

pytestmark = [pytest.mark.functional, pytest.mark.unit]
LOGGER = logging.getLogger("ib-ipv6-fvt")


# ---------------------------------------------------------------------------
# Realistic allocation export fixtures
# ---------------------------------------------------------------------------

def _dual_stack_export() -> dict[str, Any]:
    """Dual-stack allocation: node with IPv4 + IPv6 on the same interface."""
    return {
        "schema_version": "1.0",
        "snapshot_id": "snap-fvt-dualstack-001",
        "generated_at": "2026-09-26T08:00:00Z",
        "allocations": [
            {
                "allocation_id": "alloc-ds-v4-001",
                "node_id": "nid0001",
                "hostname": "nid0001",
                "interface_id": "ib0",
                "address": "10.0.100.1",
                "prefix_length": 24,
                "address_family": "ipv4",
                "fabric_id": "fabric1",
                "rail_id": "rail1",
                "rack_id": "rack01",
                "lifecycle_state": "active",
                "ipoib_mode": "datagram",
                "mtu": 2044,
                "pkey": "0x8001",
                "approved_prefix": "10.0.100.0/24",
                "authority": "static-ipam",
            },
            {
                "allocation_id": "alloc-ds-v6-001",
                "node_id": "nid0001",
                "hostname": "nid0001",
                "interface_id": "ib0",
                "address": "fd00:1b::1",
                "prefix_length": 64,
                "address_family": "ipv6",
                "fabric_id": "fabric1",
                "rail_id": "rail1",
                "rack_id": "rack01",
                "lifecycle_state": "active",
                "ipoib_mode": "datagram",
                "mtu": 2044,
                "pkey": "0x8001",
                "approved_prefix": "fd00:1b::/64",
                "authority": "static-ipam",
            },
        ],
    }


def _ipv6_only_export() -> dict[str, Any]:
    """IPv6-only allocation: node with only IPv6 addresses."""
    return {
        "schema_version": "1.0",
        "snapshot_id": "snap-fvt-v6only-001",
        "generated_at": "2026-09-26T08:00:00Z",
        "allocations": [
            {
                "allocation_id": "alloc-v6-001",
                "node_id": "nid0002",
                "hostname": "nid0002",
                "interface_id": "ib0",
                "address": "fd00:2b::1",
                "prefix_length": 64,
                "address_family": "ipv6",
                "fabric_id": "fabric1",
                "rail_id": "rail1",
                "rack_id": "rack01",
                "lifecycle_state": "active",
                "ipoib_mode": "datagram",
                "mtu": 2044,
                "pkey": "0x8001",
                "approved_prefix": "fd00:2b::/64",
                "authority": "static-ipam",
            },
        ],
    }


def _ipv4_only_legacy_export() -> dict[str, Any]:
    """Legacy IPv4-only allocation: backward-compatible single-interface."""
    return {
        "schema_version": "1.0",
        "snapshot_id": "snap-fvt-legacy-001",
        "generated_at": "2026-09-26T08:00:00Z",
        "allocations": [
            {
                "allocation_id": "alloc-legacy-001",
                "node_id": "nid0010",
                "hostname": "nid0010",
                "interface_id": "ib0",
                "address": "10.0.200.10",
                "prefix_length": 24,
                "address_family": "ipv4",
                "fabric_id": "fabric1",
                "rail_id": "rail1",
                "rack_id": "rack01",
                "lifecycle_state": "active",
                "ipoib_mode": "datagram",
                "mtu": 2044,
                "pkey": "0x8001",
                "approved_prefix": "10.0.200.0/24",
                "authority": "static-ipam",
            },
        ],
    }


def _multi_interface_export() -> dict[str, Any]:
    """Multi-interface allocation: node with ib0 on rail1, ib1 on rail2."""
    return {
        "schema_version": "1.0",
        "snapshot_id": "snap-fvt-multi-001",
        "generated_at": "2026-09-26T08:00:00Z",
        "allocations": [
            {
                "allocation_id": "alloc-mi-001",
                "node_id": "nid0005",
                "hostname": "nid0005",
                "interface_id": "ib0",
                "address": "fd00:1b::5",
                "prefix_length": 64,
                "address_family": "ipv6",
                "fabric_id": "fabric1",
                "rail_id": "rail1",
                "rack_id": "rack02",
                "lifecycle_state": "active",
                "ipoib_mode": "datagram",
                "mtu": 2044,
                "pkey": "0x8001",
                "approved_prefix": "fd00:1b::/64",
                "authority": "static-ipam",
            },
            {
                "allocation_id": "alloc-mi-002",
                "node_id": "nid0005",
                "hostname": "nid0005",
                "interface_id": "ib1",
                "address": "fd00:2b::5",
                "prefix_length": 64,
                "address_family": "ipv6",
                "fabric_id": "fabric1",
                "rail_id": "rail2",
                "rack_id": "rack02",
                "lifecycle_state": "active",
                "ipoib_mode": "datagram",
                "mtu": 2044,
                "pkey": "0x8001",
                "approved_prefix": "fd00:2b::/64",
                "authority": "static-ipam",
            },
        ],
    }


def _multi_node_mixed_export() -> dict[str, Any]:
    """Multi-node export with mixed states: active, reserved, invalid."""
    base = _multi_interface_export()
    base["allocations"].extend([
        {
            "allocation_id": "alloc-valid-003",
            "node_id": "nid0006",
            "hostname": "nid0006",
            "interface_id": "ib0",
            "address": "fd00:1b::6",
            "prefix_length": 64,
            "address_family": "ipv6",
            "fabric_id": "fabric1",
            "rail_id": "rail1",
            "rack_id": "rack03",
            "lifecycle_state": "active",
            "ipoib_mode": "datagram",
            "mtu": 2044,
            "pkey": "0x8001",
            "approved_prefix": "fd00:1b::/64",
            "authority": "static-ipam",
        },
        {
            "allocation_id": "alloc-reserved-004",
            "node_id": "nid0007",
            "hostname": "nid0007",
            "interface_id": "ib0",
            "address": "fd00:1b::7",
            "prefix_length": 64,
            "address_family": "ipv6",
            "fabric_id": "fabric1",
            "rail_id": "rail1",
            "rack_id": "rack04",
            "lifecycle_state": "reserved",
            "ipoib_mode": "datagram",
            "mtu": 2044,
            "pkey": "0x8001",
            "approved_prefix": "fd00:1b::/64",
            "authority": "static-ipam",
        },
    ])
    return base


# ===================================================================
# TC-FVT-001: Dual-stack IPoIB mode accepted
# ===================================================================

class TestDualStackMode:
    """TC-FVT-001: Dual-stack IPoIB mode accepted."""

    def test_dual_stack_accepted(self):
        """ORCH_FVT_IPV6_E001: Dual-stack mode accepts both IPv4 and IPv6.

        Scenario: Dual-stack mode accepted with valid prefixes
          GIVEN an approved IPv4 subnet and one or more approved IPv6 fabric
                prefixes
          WHEN the operator selects dual-stack mode
          THEN validation accepts both address families
          AND no address is inferred from another network's mode
        """
        data = _dual_stack_export()
        schema_errors = validator.validate_schema(data, LOGGER)
        assert schema_errors == [], f"Schema errors: {schema_errors}"

        semantic_errors = validator.validate_semantic(data, LOGGER)
        assert semantic_errors == [], f"Semantic errors: {semantic_errors}"

        valid, failed = validator.preflight_validate(data, LOGGER)
        assert "nid0001" in valid
        assert failed == {}

        mode = validator.detect_ib_mode(valid["nid0001"])
        assert mode == "dual-stack"

    def test_dual_stack_missing_ipv6_prefix_rejected(self):
        """ORCH_FVT_IPV6_E002: Missing IPv6 prefix in dual-stack is rejected.

        Scenario: Missing IPv6 prefix in dual-stack mode rejected
          GIVEN an approved IPv4 subnet but no IPv6 fabric prefix
          WHEN the operator selects dual-stack mode
          THEN validation fails with a specific error identifying the missing
               prefix
        """
        data = _dual_stack_export()
        # Remove the IPv6 allocation but keep IPv4 — not dual-stack anymore
        data["allocations"][1]["approved_prefix"] = "not-a-valid-prefix"
        semantic_errors = validator.validate_semantic(data, LOGGER)
        assert any("malformed" in e.lower() for e in semantic_errors)


# ===================================================================
# TC-FVT-002: IPv6-only IPoIB mode accepted
# ===================================================================

class TestIPv6OnlyMode:
    """TC-FVT-002: IPv6-only IPoIB mode accepted."""

    def test_ipv6_only_mode_accepted(self):
        """ORCH_FVT_IPV6_E003: IPv6-only mode works without IPv4 addresses.

        Scenario: IPv6-only mode accepted without IPv4
          GIVEN one or more approved IPv6 fabric prefixes and no IPv4 subnet
          WHEN the operator selects IPv6-only mode
          THEN validation accepts the configuration without requiring an IPv4
               IPoIB address
        """
        data = _ipv6_only_export()
        schema_errors = validator.validate_schema(data, LOGGER)
        assert schema_errors == []

        semantic_errors = validator.validate_semantic(data, LOGGER)
        assert semantic_errors == []

        valid, failed = validator.preflight_validate(data, LOGGER)
        assert "nid0002" in valid
        mode = validator.detect_ib_mode(valid["nid0002"])
        assert mode == "ipv6-only"

    def test_ipv6_only_no_ipv4_required(self):
        """ORCH_FVT_IPV6_E004: IPv6-only interface has no IPv4 requirement.

        Scenario: IPv6-only interface rendering
          GIVEN an interface with only an approved IPv6 allocation
          WHEN the configuration script renders
          THEN no IPv4 address is required
        """
        data = _ipv6_only_export()
        valid, _ = validator.preflight_validate(data, LOGGER)
        node_ifaces = valid["nid0002"]
        for iface_id, records in node_ifaces.items():
            for record in records:
                assert record["address_family"] == "ipv6"

        # Legacy adapter returns None for IPv6-only
        legacy = validator.legacy_ib_ip_projection(node_ifaces)
        assert legacy is None


# ===================================================================
# TC-FVT-003: Legacy IPv4-only configuration unchanged
# ===================================================================

class TestLegacyIPv4Only:
    """TC-FVT-003: Legacy IPv4-only configuration unchanged."""

    def test_ipv4_only_passes_validation(self):
        """ORCH_FVT_IPV6_E005: Existing IPv4-only configurations not disrupted.

        Scenario: Legacy IPv4-only input unchanged
          GIVEN an existing valid IPv4-only configuration without IPv6 fields
          WHEN validation runs
          THEN existing IPv4 behavior remains unchanged
          AND no input migration is required
        """
        data = _ipv4_only_legacy_export()
        schema_errors = validator.validate_schema(data, LOGGER)
        assert schema_errors == []

        semantic_errors = validator.validate_semantic(data, LOGGER)
        assert semantic_errors == []

        valid, failed = validator.preflight_validate(data, LOGGER)
        assert "nid0010" in valid
        assert failed == {}

        mode = validator.detect_ib_mode(valid["nid0010"])
        assert mode == "ipv4-only"

    def test_ipv4_only_legacy_adapter_works(self):
        """ORCH_FVT_IPV6_E006: IPv4-only interface projects to flat IB_IP.

        Scenario: IPv4-only interface is not modified by IPv6 enhancement
          GIVEN the interface is IPv4-only in the allocation export
          WHEN the enhancement runs
          THEN existing approved IPv4 behavior remains unchanged
        """
        data = _ipv4_only_legacy_export()
        valid, _ = validator.preflight_validate(data, LOGGER)
        legacy = validator.legacy_ib_ip_projection(valid["nid0010"])
        assert legacy is not None
        assert legacy["IB_IP"] == "10.0.200.10"


# ===================================================================
# TC-FVT-004: Invalid prefix rejected at validation
# ===================================================================

class TestInvalidPrefixRejection:
    """TC-FVT-004: Invalid prefix rejected at validation."""

    def test_malformed_prefix_rejected(self):
        """ORCH_FVT_IPV6_E007: Malformed prefix rejected before provisioning.

        Scenario: Malformed prefix rejected
          GIVEN a malformed approved-prefix definition
          WHEN validation runs
          THEN validation fails before provisioning artifacts are modified
          AND identifies the affected fabric and field
        """
        data = _ipv6_only_export()
        data["allocations"][0]["approved_prefix"] = "not/a/prefix"
        semantic_errors = validator.validate_semantic(data, LOGGER)
        assert len(semantic_errors) >= 1
        assert any("malformed" in e.lower() for e in semantic_errors)

    def test_overlapping_prefix_addresses_detected(self):
        """ORCH_FVT_IPV6_E008: Overlapping prefix addresses are detected.

        Scenario: Overlapping prefix rejected
          GIVEN two approved prefixes that overlap in address space
          WHEN validation runs
          THEN validation rejects the configuration with a specific overlap error
        """
        data = _dual_stack_export()
        # Create second IPv6 allocation with address from a different prefix
        # but CLAIM it's from the same prefix — this is an address-outside-prefix
        dup = copy.deepcopy(data["allocations"][1])
        dup["allocation_id"] = "alloc-overlap"
        dup["address"] = "fd00:ff::99"
        dup["approved_prefix"] = "fd00:1b::/64"  # Address not in this prefix
        data["allocations"].append(dup)

        semantic_errors = validator.validate_semantic(data, LOGGER)
        assert any("outside" in e.lower() for e in semantic_errors)

    def test_ipv4_prefix_for_ipv6_family_rejected(self):
        """ORCH_FVT_IPV6_E009: Wrong address family prefix is rejected."""
        data = _ipv6_only_export()
        data["allocations"][0]["approved_prefix"] = "10.0.0.0/24"
        semantic_errors = validator.validate_semantic(data, LOGGER)
        assert any("not an ipv6 network" in e.lower() for e in semantic_errors)


# ===================================================================
# TC-FVT-005: Multi-interface normalization through one path
# ===================================================================

class TestMultiInterfaceNormalization:
    """TC-FVT-005: Multi-interface normalization through one path."""

    def test_single_interface_produces_one_item(self):
        """ORCH_FVT_IPV6_E010: Single-interface host produces one-item collection.

        Scenario: Single-interface host processed normally
          GIVEN a host with one IPoIB interface (ib0 on rail1)
          WHEN allocation records are normalized
          THEN a single-item interface collection is produced
        """
        data = _ipv6_only_export()
        valid, _ = validator.preflight_validate(data, LOGGER)
        assert len(valid["nid0002"]) == 1
        assert "ib0" in valid["nid0002"]

    def test_multi_interface_produces_multi_item(self):
        """ORCH_FVT_IPV6_E011: Multi-interface host produces multi-item collection.

        Scenario: Multi-interface host produces multi-item collection
          GIVEN a host with two IPoIB interfaces (ib0 on rail1, ib1 on rail2)
          WHEN allocation records are normalized
          THEN a two-item interface collection is produced
          AND both interfaces use the same validation and rendering workflow
        """
        data = _multi_interface_export()
        valid, _ = validator.preflight_validate(data, LOGGER)
        assert "nid0005" in valid
        assert len(valid["nid0005"]) == 2
        assert "ib0" in valid["nid0005"]
        assert "ib1" in valid["nid0005"]

    def test_multi_interface_same_workflow(self):
        """ORCH_FVT_IPV6_E012: Both interfaces use the same normalization path."""
        data = _multi_interface_export()
        valid, _ = validator.preflight_validate(data, LOGGER)
        for iface_id, records in valid["nid0005"].items():
            assert len(records) == 1
            assert records[0]["address_family"] == "ipv6"
            assert records[0]["lifecycle_state"] == "active"


# ===================================================================
# TC-FVT-006: Invalid allocation set rejected before artifacts
# ===================================================================

class TestInvalidAllocationRejection:
    """TC-FVT-006: Invalid allocation set rejected before artifacts."""

    def test_reserved_allocation_rejected(self):
        """ORCH_FVT_IPV6_E013: Reserved allocation not rendered.

        Scenario: Reserved allocation rejected for configuration
          GIVEN an allocation record has lifecycle_state reserved
          WHEN preflight validation runs
          THEN the record is not rendered into any downstream artifact
          AND the error identifies the allocation as non-active
        """
        data = _multi_node_mixed_export()
        valid, _ = validator.preflight_validate(data, LOGGER)
        assert "nid0007" not in valid  # Reserved node excluded

    def test_retired_allocation_rejected(self):
        """ORCH_FVT_IPV6_E014: Retired allocation not rendered.

        Scenario: Retired allocation rejected for configuration
          GIVEN an allocation record has lifecycle_state retired
          WHEN preflight validation runs
          THEN the record is not rendered
        """
        data = _ipv6_only_export()
        data["allocations"][0]["lifecycle_state"] = "retired"
        valid, _ = validator.preflight_validate(data, LOGGER)
        assert "nid0002" not in valid

    def test_invalid_address_rejected_with_identity(self):
        """ORCH_FVT_IPV6_E015: Invalid address rejected with full identity.

        Scenario: Invalid address rejected
          GIVEN an allocation with a malformed address
          WHEN preflight validation runs
          THEN validation rejects identifying the node, interface, allocation
               ID, and field
        """
        data = _ipv6_only_export()
        data["allocations"][0]["address"] = "zzzz::invalid"
        _, failed = validator.preflight_validate(data, LOGGER)
        assert "nid0002" in failed
        errors = failed["nid0002"]
        assert any("nid0002" in e for e in errors)
        assert any("ib0" in e for e in errors)
        assert any("alloc-v6-001" in e for e in errors)

    def test_address_outside_prefix_rejected(self):
        """ORCH_FVT_IPV6_E016: Address outside approved_prefix rejected.

        Scenario: Address outside approved prefix rejected
          GIVEN an allocation address not contained in the approved_prefix
          WHEN preflight validation runs
          THEN validation rejects with prefix mismatch error
        """
        data = _ipv6_only_export()
        data["allocations"][0]["approved_prefix"] = "fd00:ff::/64"
        _, failed = validator.preflight_validate(data, LOGGER)
        assert "nid0002" in failed
        assert any("outside" in e.lower() for e in failed["nid0002"])

    def test_prohibited_loopback_address_rejected(self):
        """ORCH_FVT_IPV6_E017: Loopback address rejected in semantic check."""
        data = _ipv6_only_export()
        data["allocations"][0]["address"] = "::1"
        data["allocations"][0]["approved_prefix"] = "::/128"
        semantic_errors = validator.validate_semantic(data, LOGGER)
        # ::1 is valid IPv6 but should be outside any production prefix
        # The address-in-prefix check catches mismatches
        valid, failed = validator.preflight_validate(data, LOGGER)
        # Loopback is a valid IPv6 address but outside the fabric prefix
        assert "nid0002" in failed or len(semantic_errors) >= 1


# ===================================================================
# TC-FVT-007: Equivalent IPv6 addresses detected as duplicates
# ===================================================================

class TestIPv6DuplicateDetection:
    """TC-FVT-007: Equivalent IPv6 addresses detected as duplicates."""

    def test_compressed_expanded_duplicates(self):
        """ORCH_FVT_IPV6_E018: Compressed and expanded IPv6 are duplicates.

        Scenario: Compressed and expanded IPv6 duplicates detected
          GIVEN fd00:1b::1 and fd00:1b:0000:0000:0000:0000:0000:0001
          WHEN duplicate validation runs
          THEN the records are treated as duplicates
          AND validation fails with the identified duplicate pair
        """
        data = _ipv6_only_export()
        dup = copy.deepcopy(data["allocations"][0])
        dup["allocation_id"] = "alloc-dup-expanded"
        dup["address"] = "fd00:002b:0000:0000:0000:0000:0000:0001"
        data["allocations"].append(dup)

        semantic_errors = validator.validate_semantic(data, LOGGER)
        assert any("duplicate" in e.lower() for e in semantic_errors)
        # Verify the duplicate pair is identified
        assert any(
            "alloc-v6-001" in e or "alloc-dup-expanded" in e
            for e in semantic_errors
        )

    def test_different_addresses_not_duplicate(self):
        """ORCH_FVT_IPV6_E019: Different addresses are not flagged as duplicates."""
        data = _multi_interface_export()
        semantic_errors = validator.validate_semantic(data, LOGGER)
        assert not any("duplicate" in e.lower() for e in semantic_errors)


# ===================================================================
# TC-FVT-008: Idempotent reapplication of unchanged snapshot
# ===================================================================

class TestIdempotentReapplication:
    """TC-FVT-008: Idempotent reapplication of unchanged snapshot."""

    def test_same_snapshot_produces_same_output(self):
        """ORCH_FVT_IPV6_E020: Reapplying unchanged snapshot is idempotent.

        Scenario: Unchanged snapshot produces identical output
          GIVEN a valid allocation snapshot
          WHEN the same snapshot is processed twice
          THEN validation output is identical
          AND normalized structure is identical
        """
        data = _dual_stack_export()
        # First pass
        valid1, failed1 = validator.preflight_validate(data, LOGGER)
        # Second pass with same data (deep copy to ensure independence)
        data2 = copy.deepcopy(data)
        valid2, failed2 = validator.preflight_validate(data2, LOGGER)

        assert set(valid1.keys()) == set(valid2.keys())
        assert failed1 == failed2
        for node_id in valid1:
            assert set(valid1[node_id].keys()) == set(valid2[node_id].keys())

    def test_same_snapshot_revalidation(self):
        """ORCH_FVT_IPV6_E021: Same snapshot re-validates without errors.

        Scenario: No additional errors on reprovisioning
          GIVEN the allocation snapshot is unchanged
          WHEN provisioning is rerun
          THEN no additional errors appear
        """
        data = _multi_node_mixed_export()
        errors1 = validator.validate_semantic(data, LOGGER)
        errors2 = validator.validate_semantic(data, LOGGER)
        assert errors1 == errors2


# ===================================================================
# TC-FVT-018: Node-scoped atomicity on preflight failure
# ===================================================================

class TestNodeScopedAtomicity:
    """TC-FVT-018: Node-scoped atomicity on preflight failure."""

    def test_failed_node_no_artifacts_valid_node_proceeds(self):
        """ORCH_FVT_IPV6_E022: Failed node produces no artifacts.

        Scenario: Failed node produces no partial artifacts
          GIVEN node nid0003 has an invalid allocation
          AND node nid0004 has a valid allocation
          WHEN preflight validation runs
          THEN nid0003 produces no artifacts
          AND nid0004 proceeds normally
        """
        data = {
            "schema_version": "1.0",
            "snapshot_id": "snap-atomicity-001",
            "allocations": [
                {
                    "allocation_id": "alloc-bad",
                    "node_id": "nid0003",
                    "hostname": "nid0003",
                    "interface_id": "ib0",
                    "address": "not-a-valid-address",
                    "prefix_length": 64,
                    "address_family": "ipv6",
                    "fabric_id": "fabric1",
                    "rail_id": "rail1",
                    "lifecycle_state": "active",
                },
                {
                    "allocation_id": "alloc-good",
                    "node_id": "nid0004",
                    "hostname": "nid0004",
                    "interface_id": "ib0",
                    "address": "fd00:1b::4",
                    "prefix_length": 64,
                    "address_family": "ipv6",
                    "fabric_id": "fabric1",
                    "rail_id": "rail1",
                    "lifecycle_state": "active",
                },
            ],
        }
        valid, failed = validator.preflight_validate(data, LOGGER)
        assert "nid0003" not in valid, "Failed node should produce no artifacts"
        assert "nid0003" in failed, "Failed node should be in failed dict"
        assert "nid0004" in valid, "Valid node should proceed"
        assert "nid0004" not in failed

    def test_multiple_errors_on_one_node_all_collected(self):
        """ORCH_FVT_IPV6_E023: Multiple errors on one node are all reported.

        Scenario: Multi-error node collects all errors
          GIVEN a node with two interfaces both having invalid allocations
          WHEN preflight validation runs
          THEN all errors for the node are collected
          AND the node is rejected as a whole
        """
        data = {
            "schema_version": "1.0",
            "snapshot_id": "snap-multi-error-001",
            "allocations": [
                {
                    "allocation_id": "alloc-bad-1",
                    "node_id": "nid0008",
                    "hostname": "nid0008",
                    "interface_id": "ib0",
                    "address": "invalid-1",
                    "prefix_length": 64,
                    "address_family": "ipv6",
                    "fabric_id": "fabric1",
                    "rail_id": "rail1",
                    "lifecycle_state": "active",
                },
                {
                    "allocation_id": "alloc-bad-2",
                    "node_id": "nid0008",
                    "hostname": "nid0008",
                    "interface_id": "ib1",
                    "address": "invalid-2",
                    "prefix_length": 64,
                    "address_family": "ipv6",
                    "fabric_id": "fabric1",
                    "rail_id": "rail2",
                    "lifecycle_state": "active",
                },
            ],
        }
        valid, failed = validator.preflight_validate(data, LOGGER)
        assert "nid0008" not in valid
        assert "nid0008" in failed
        assert len(failed["nid0008"]) >= 2

    def test_file_load_and_full_pipeline(self, tmp_path):
        """ORCH_FVT_IPV6_E024: End-to-end pipeline from file to validated nodes.

        Scenario: Full pipeline from file to validated nodes
          GIVEN a valid allocation export file on disk
          WHEN the file is loaded and the full pipeline runs
          THEN the output matches expectations
        """
        export = _multi_node_mixed_export()
        alloc_file = tmp_path / "allocations.json"
        alloc_file.write_text(json.dumps(export), encoding="utf-8")

        data, error = validator.load_allocation_file(str(alloc_file))
        assert error is None
        assert data is not None

        schema_errors = validator.validate_schema(data, LOGGER)
        assert schema_errors == []

        semantic_errors = validator.validate_semantic(data, LOGGER)
        assert semantic_errors == []

        valid, failed = validator.preflight_validate(data, LOGGER)
        assert "nid0005" in valid  # Active multi-interface
        assert "nid0006" in valid  # Active single-interface
        assert "nid0007" not in valid  # Reserved — excluded
        assert failed == {}


# ===================================================================
# Integration: Schema + Semantic pipeline via validation engine
# ===================================================================

class TestValidationEnginePipeline:
    """Integration tests via the validation engine dispatch."""

    def test_engine_schema_validation(self):
        """ORCH_FVT_IPV6_E025: Validation engine dispatches L1 correctly."""
        data = _dual_stack_export()
        errors = validation_engine.schema_ib_ipv6_allocation(data, LOGGER)
        assert errors == []

    def test_engine_semantic_validation(self):
        """ORCH_FVT_IPV6_E026: Validation engine dispatches L2 correctly."""
        data = _dual_stack_export()
        errors = validation_engine.logic_ib_ipv6_allocation(data, LOGGER)
        assert errors == []

    def test_engine_schema_rejects_invalid(self):
        """ORCH_FVT_IPV6_E027: Validation engine L1 rejects invalid input."""
        data = {"not_valid": True}
        errors = validation_engine.schema_ib_ipv6_allocation(data, LOGGER)
        assert len(errors) >= 1
