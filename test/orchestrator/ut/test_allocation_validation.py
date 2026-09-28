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
"""Unit tests for IPoIB IPv6 allocation import, validation, and normalization.

Covers ER-ORCH-005 test plan cases TC-UT-001 through TC-UT-004.
"""

import copy
import json
import logging

import pytest

from ut import source_loader  # noqa: F401  # initializes module_utils path
from ansible.module_utils.orchestrator_validation.validators import (
    ib_ipv6_allocation_validator as validator,
)

pytestmark = pytest.mark.unit
LOGGER = logging.getLogger("ib-ipv6-allocation-test")


# ---------------------------------------------------------------------------
# Fixtures — canonical valid allocation export
# ---------------------------------------------------------------------------

def _valid_allocation_export():
    """Return a minimal valid allocation export document."""
    return {
        "schema_version": "1.0",
        "snapshot_id": "snap-20260925-001",
        "generated_at": "2026-09-25T12:00:00Z",
        "allocations": [
            {
                "allocation_id": "alloc-001",
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


def _dual_interface_export():
    """Return an export with a dual-interface node (ib0 + ib1)."""
    base = _valid_allocation_export()
    base["allocations"].append({
        "allocation_id": "alloc-002",
        "node_id": "nid0001",
        "hostname": "nid0001",
        "interface_id": "ib1",
        "address": "fd00:2b::1",
        "prefix_length": 64,
        "address_family": "ipv6",
        "fabric_id": "fabric1",
        "rail_id": "rail2",
        "rack_id": "rack01",
        "lifecycle_state": "active",
        "ipoib_mode": "datagram",
        "mtu": 2044,
        "pkey": "0x8001",
        "approved_prefix": "fd00:2b::/64",
        "authority": "static-ipam",
    })
    return base


def _ipv4_single_interface_export():
    """Return an export with a single IPv4 IB allocation (legacy path)."""
    return {
        "schema_version": "1.0",
        "snapshot_id": "snap-legacy-001",
        "allocations": [
            {
                "allocation_id": "alloc-v4-001",
                "node_id": "nid0010",
                "hostname": "nid0010",
                "interface_id": "ib0",
                "address": "10.0.1.10",
                "prefix_length": 24,
                "address_family": "ipv4",
                "fabric_id": "fabric1",
                "rail_id": "rail1",
                "lifecycle_state": "active",
            },
        ],
    }


# ===================================================================
# TC-UT-001: Schema Validator — allocation export JSON schema
# ===================================================================

class TestSchemaValidator:
    """TC-UT-001: Schema Validator — allocation export JSON schema."""

    def test_valid_allocation_passes_schema(self):
        """ORCH_UT_100: Valid allocation export passes L1 schema validation."""
        data = _valid_allocation_export()
        errors = validator.validate_schema(data, LOGGER)
        assert errors == []

    def test_missing_schema_version_rejected(self):
        """ORCH_UT_101: Missing schema_version is rejected by L1 schema."""
        data = _valid_allocation_export()
        del data["schema_version"]
        errors = validator.validate_schema(data, LOGGER)
        assert len(errors) >= 1
        assert any("schema_version" in e or "required" in e for e in errors)

    def test_missing_snapshot_id_rejected(self):
        """ORCH_UT_102: Missing snapshot_id is rejected by L1 schema."""
        data = _valid_allocation_export()
        del data["snapshot_id"]
        errors = validator.validate_schema(data, LOGGER)
        assert len(errors) >= 1

    def test_missing_allocations_rejected(self):
        """ORCH_UT_103: Missing allocations array is rejected."""
        data = _valid_allocation_export()
        del data["allocations"]
        errors = validator.validate_schema(data, LOGGER)
        assert len(errors) >= 1

    def test_allocation_missing_required_field_rejected(self):
        """ORCH_UT_104: Allocation missing required field (address) is rejected."""
        data = _valid_allocation_export()
        del data["allocations"][0]["address"]
        errors = validator.validate_schema(data, LOGGER)
        assert len(errors) >= 1

    def test_invalid_lifecycle_state_rejected(self):
        """ORCH_UT_105: Invalid lifecycle_state enum value is rejected."""
        data = _valid_allocation_export()
        data["allocations"][0]["lifecycle_state"] = "unknown"
        errors = validator.validate_schema(data, LOGGER)
        assert len(errors) >= 1

    def test_invalid_address_family_rejected(self):
        """ORCH_UT_106: Invalid address_family enum value is rejected."""
        data = _valid_allocation_export()
        data["allocations"][0]["address_family"] = "ipv8"
        errors = validator.validate_schema(data, LOGGER)
        assert len(errors) >= 1

    def test_invalid_pkey_format_rejected(self):
        """ORCH_UT_107: Invalid pkey format is rejected."""
        data = _valid_allocation_export()
        data["allocations"][0]["pkey"] = "ZZZZ"
        errors = validator.validate_schema(data, LOGGER)
        assert len(errors) >= 1

    def test_additional_properties_rejected(self):
        """ORCH_UT_108: Extra properties on the root object are rejected."""
        data = _valid_allocation_export()
        data["extra_field"] = "should fail"
        errors = validator.validate_schema(data, LOGGER)
        assert len(errors) >= 1

    def test_empty_allocations_array_passes(self):
        """ORCH_UT_109: Empty allocations array is valid (no nodes to configure)."""
        data = _valid_allocation_export()
        data["allocations"] = []
        errors = validator.validate_schema(data, LOGGER)
        assert errors == []


# ===================================================================
# TC-UT-002: Semantic Validator — cross-field and cross-file checks
# ===================================================================

class TestSemanticValidator:
    """TC-UT-002: Semantic Validator — cross-field and cross-file checks."""

    def test_valid_export_passes_semantic(self):
        """ORCH_UT_110: Valid allocation export passes L2 semantic validation."""
        data = _valid_allocation_export()
        errors = validator.validate_semantic(data, LOGGER)
        assert errors == []

    def test_unsupported_schema_version_rejected(self):
        """ORCH_UT_111: Unsupported schema_version is rejected."""
        data = _valid_allocation_export()
        data["schema_version"] = "99.0"
        errors = validator.validate_semantic(data, LOGGER)
        assert len(errors) >= 1
        assert any("schema_version" in e for e in errors)

    def test_invalid_ipv6_address_rejected(self):
        """ORCH_UT_112: Malformed IPv6 address is rejected."""
        data = _valid_allocation_export()
        data["allocations"][0]["address"] = "not-an-ipv6"
        errors = validator.validate_semantic(data, LOGGER)
        assert len(errors) >= 1
        assert any("not a valid ipv6" in e for e in errors)

    def test_invalid_ipv4_address_rejected(self):
        """ORCH_UT_113: Malformed IPv4 address is rejected."""
        data = _ipv4_single_interface_export()
        data["allocations"][0]["address"] = "999.999.999.999"
        errors = validator.validate_semantic(data, LOGGER)
        assert len(errors) >= 1

    def test_ipv6_compressed_expanded_duplicate_detected(self):
        """ORCH_UT_114: Compressed and expanded IPv6 duplicates detected."""
        data = _valid_allocation_export()
        dup = copy.deepcopy(data["allocations"][0])
        dup["allocation_id"] = "alloc-dup"
        dup["address"] = "fd00:001b:0000:0000:0000:0000:0000:0001"
        data["allocations"].append(dup)
        errors = validator.validate_semantic(data, LOGGER)
        assert any("duplicate" in e.lower() for e in errors)

    def test_malformed_approved_prefix_rejected(self):
        """ORCH_UT_115: Malformed approved_prefix is rejected."""
        data = _valid_allocation_export()
        data["allocations"][0]["approved_prefix"] = "not-a-prefix"
        errors = validator.validate_semantic(data, LOGGER)
        assert any("malformed" in e.lower() for e in errors)

    def test_address_outside_prefix_rejected(self):
        """ORCH_UT_116: Address outside its approved_prefix is rejected."""
        data = _valid_allocation_export()
        data["allocations"][0]["approved_prefix"] = "fd00:ff::/64"
        errors = validator.validate_semantic(data, LOGGER)
        assert any("outside" in e.lower() for e in errors)

    def test_ipv6_prefix_for_ipv4_family_rejected(self):
        """ORCH_UT_117: IPv6 prefix with ipv4 address_family is rejected."""
        data = _ipv4_single_interface_export()
        data["allocations"][0]["approved_prefix"] = "fd00:1b::/64"
        errors = validator.validate_semantic(data, LOGGER)
        assert any("not an ipv4 network" in e.lower() for e in errors)

    def test_invalid_lifecycle_state_in_semantic(self):
        """ORCH_UT_118: Unknown lifecycle_state flagged in semantic check."""
        data = _valid_allocation_export()
        data["allocations"][0]["lifecycle_state"] = "decommissioned"
        errors = validator.validate_semantic(data, LOGGER)
        assert any("lifecycle_state" in e for e in errors)


# ===================================================================
# TC-UT-003: Allocation Normalizer — per-node, per-interface grouping
# ===================================================================

class TestAllocationNormalizer:
    """TC-UT-003: Allocation Normalizer — per-node, per-interface grouping."""

    def test_single_interface_grouped(self):
        """ORCH_UT_120: Single-interface node produces single-item collection."""
        data = _valid_allocation_export()
        active, _ = validator.filter_active(data["allocations"])
        per_node = validator.normalize_per_node(active)
        assert "nid0001" in per_node
        assert "ib0" in per_node["nid0001"]
        assert len(per_node["nid0001"]["ib0"]) == 1

    def test_multi_interface_grouped(self):
        """ORCH_UT_121: Multi-interface host produces multi-item collection."""
        data = _dual_interface_export()
        active, _ = validator.filter_active(data["allocations"])
        per_node = validator.normalize_per_node(active)
        assert "nid0001" in per_node
        assert len(per_node["nid0001"]) == 2
        assert "ib0" in per_node["nid0001"]
        assert "ib1" in per_node["nid0001"]

    def test_active_filtering(self):
        """ORCH_UT_122: Only active allocations pass lifecycle filter."""
        data = _valid_allocation_export()
        reserved = copy.deepcopy(data["allocations"][0])
        reserved["allocation_id"] = "alloc-reserved"
        reserved["lifecycle_state"] = "reserved"
        reserved["address"] = "fd00:1b::99"
        data["allocations"].append(reserved)

        active, excluded = validator.filter_active(data["allocations"])
        assert len(active) == 1
        assert len(excluded) == 1
        assert excluded[0]["lifecycle_state"] == "reserved"

    def test_retired_excluded(self):
        """ORCH_UT_123: Retired allocations are excluded from configuration."""
        data = _valid_allocation_export()
        data["allocations"][0]["lifecycle_state"] = "retired"
        active, excluded = validator.filter_active(data["allocations"])
        assert len(active) == 0
        assert len(excluded) == 1

    def test_all_reserved_produces_empty(self):
        """ORCH_UT_124: All-reserved input produces empty normalized output."""
        data = _valid_allocation_export()
        data["allocations"][0]["lifecycle_state"] = "reserved"
        active, _ = validator.filter_active(data["allocations"])
        per_node = validator.normalize_per_node(active)
        assert per_node == {}

    def test_multiple_nodes_grouped_separately(self):
        """ORCH_UT_125: Allocations for different nodes are grouped separately."""
        data = _valid_allocation_export()
        node2 = copy.deepcopy(data["allocations"][0])
        node2["allocation_id"] = "alloc-n2"
        node2["node_id"] = "nid0002"
        node2["hostname"] = "nid0002"
        node2["address"] = "fd00:1b::2"
        data["allocations"].append(node2)

        active, _ = validator.filter_active(data["allocations"])
        per_node = validator.normalize_per_node(active)
        assert len(per_node) == 2
        assert "nid0001" in per_node
        assert "nid0002" in per_node


# ===================================================================
# TC-UT-004: Legacy Adapter — IB_IP compatibility projection
# ===================================================================

class TestLegacyAdapter:
    """TC-UT-004: Legacy Adapter — IB_IP compatibility projection."""

    def test_single_ipv4_interface_projects_ib_ip(self):
        """ORCH_UT_130: Single IPv4 interface projects to flat IB_IP."""
        data = _ipv4_single_interface_export()
        active, _ = validator.filter_active(data["allocations"])
        per_node = validator.normalize_per_node(active)
        result = validator.legacy_ib_ip_projection(per_node["nid0010"])
        assert result is not None
        assert result["IB_IP"] == "10.0.1.10"

    def test_multi_interface_returns_none(self):
        """ORCH_UT_131: Multi-interface node returns None (no legacy projection)."""
        data = _dual_interface_export()
        active, _ = validator.filter_active(data["allocations"])
        per_node = validator.normalize_per_node(active)
        result = validator.legacy_ib_ip_projection(per_node["nid0001"])
        assert result is None

    def test_ipv6_only_interface_returns_none(self):
        """ORCH_UT_132: IPv6-only interface returns None (no IB_IP for IPv6)."""
        data = _valid_allocation_export()
        active, _ = validator.filter_active(data["allocations"])
        per_node = validator.normalize_per_node(active)
        result = validator.legacy_ib_ip_projection(per_node["nid0001"])
        assert result is None


# ===================================================================
# Additional: IPv6 normalization and IB mode detection
# ===================================================================

class TestIPv6Normalization:
    """IPv6 normalization utility tests."""

    def test_compressed_form(self):
        """ORCH_UT_140: Expanded IPv6 normalizes to compressed form."""
        result = validator.normalize_ipv6(
            "fd00:001b:0000:0000:0000:0000:0000:0001"
        )
        assert result == "fd00:1b::1"

    def test_already_compressed(self):
        """ORCH_UT_141: Already-compressed IPv6 is idempotent."""
        result = validator.normalize_ipv6("fd00:1b::1")
        assert result == "fd00:1b::1"

    def test_invalid_ipv6_returns_none(self):
        """ORCH_UT_142: Invalid IPv6 string returns None."""
        assert validator.normalize_ipv6("not-ipv6") is None

    def test_empty_string_returns_none(self):
        """ORCH_UT_143: Empty string returns None."""
        assert validator.normalize_ipv6("") is None


class TestIBModeDetection:
    """IB address-family mode detection tests."""

    def test_ipv6_only_mode(self):
        """ORCH_UT_150: IPv6-only allocations detected as ipv6-only mode."""
        data = _valid_allocation_export()
        active, _ = validator.filter_active(data["allocations"])
        per_node = validator.normalize_per_node(active)
        mode = validator.detect_ib_mode(per_node["nid0001"])
        assert mode == "ipv6-only"

    def test_ipv4_only_mode(self):
        """ORCH_UT_151: IPv4-only allocations detected as ipv4-only mode."""
        data = _ipv4_single_interface_export()
        active, _ = validator.filter_active(data["allocations"])
        per_node = validator.normalize_per_node(active)
        mode = validator.detect_ib_mode(per_node["nid0010"])
        assert mode == "ipv4-only"

    def test_dual_stack_mode(self):
        """ORCH_UT_152: Mixed IPv4+IPv6 allocations detected as dual-stack."""
        data = _valid_allocation_export()
        ipv4_record = {
            "allocation_id": "alloc-v4",
            "node_id": "nid0001",
            "hostname": "nid0001",
            "interface_id": "ib0",
            "address": "10.0.1.1",
            "prefix_length": 24,
            "address_family": "ipv4",
            "fabric_id": "fabric1",
            "rail_id": "rail1",
            "lifecycle_state": "active",
        }
        data["allocations"].append(ipv4_record)
        active, _ = validator.filter_active(data["allocations"])
        per_node = validator.normalize_per_node(active)
        mode = validator.detect_ib_mode(per_node["nid0001"])
        assert mode == "dual-stack"


# ===================================================================
# Node-scoped atomicity
# ===================================================================

class TestNodeScopedAtomicity:
    """Node-scoped preflight atomicity tests."""

    def test_valid_node_passes_preflight(self):
        """ORCH_UT_160: Valid node passes preflight with no errors."""
        data = _valid_allocation_export()
        valid, failed = validator.preflight_validate(data, LOGGER)
        assert "nid0001" in valid
        assert failed == {}

    def test_invalid_node_rejected_valid_node_proceeds(self):
        """ORCH_UT_161: Failed node produces no artifacts; valid node proceeds."""
        data = _valid_allocation_export()
        bad_record = {
            "allocation_id": "alloc-bad",
            "node_id": "nid0003",
            "hostname": "nid0003",
            "interface_id": "ib0",
            "address": "not-valid",
            "prefix_length": 64,
            "address_family": "ipv6",
            "fabric_id": "fabric1",
            "rail_id": "rail1",
            "lifecycle_state": "active",
        }
        data["allocations"].append(bad_record)
        valid, failed = validator.preflight_validate(data, LOGGER)
        assert "nid0001" in valid
        assert "nid0003" in failed
        assert len(failed["nid0003"]) >= 1

    def test_reserved_allocations_excluded_from_preflight(self):
        """ORCH_UT_162: Reserved allocations are silently excluded."""
        data = _valid_allocation_export()
        reserved = copy.deepcopy(data["allocations"][0])
        reserved["allocation_id"] = "alloc-res"
        reserved["node_id"] = "nid0099"
        reserved["hostname"] = "nid0099"
        reserved["lifecycle_state"] = "reserved"
        reserved["address"] = "fd00:1b::99"
        data["allocations"].append(reserved)

        valid, failed = validator.preflight_validate(data, LOGGER)
        assert "nid0001" in valid
        assert "nid0099" not in valid
        assert "nid0099" not in failed

    def test_address_outside_prefix_fails_node(self):
        """ORCH_UT_163: Address outside approved_prefix fails the entire node."""
        data = _valid_allocation_export()
        data["allocations"][0]["approved_prefix"] = "fd00:ff::/64"
        valid, failed = validator.preflight_validate(data, LOGGER)
        assert "nid0001" not in valid
        assert "nid0001" in failed


# ===================================================================
# File loading
# ===================================================================

class TestFileLoading:
    """Allocation file loading tests."""

    def test_load_valid_file(self, tmp_path):
        """ORCH_UT_170: Valid JSON file loads successfully."""
        path = tmp_path / "allocations.json"
        data = _valid_allocation_export()
        path.write_text(json.dumps(data), encoding="utf-8")
        result, error = validator.load_allocation_file(str(path))
        assert error is None
        assert result is not None
        assert result["schema_version"] == "1.0"

    def test_load_missing_file(self):
        """ORCH_UT_171: Missing file returns error."""
        result, error = validator.load_allocation_file("/nonexistent/path.json")
        assert result is None
        assert "not found" in error.lower()

    def test_load_invalid_json(self, tmp_path):
        """ORCH_UT_172: Invalid JSON returns parse error."""
        path = tmp_path / "bad.json"
        path.write_text("{invalid json", encoding="utf-8")
        result, error = validator.load_allocation_file(str(path))
        assert result is None
        assert "parse" in error.lower() or "failed" in error.lower()
