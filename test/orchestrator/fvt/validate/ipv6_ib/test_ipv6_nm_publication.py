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
"""FVT: NM configuration, SMD registration, and hostname publication (ER-ORCH-005).

Covers TC-FVT-009 through TC-FVT-013 from the ER test plan.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

import pytest

from ut import source_loader  # noqa: F401
from ansible.module_utils.orchestrator_validation.renderers import (
    nm_renderer,
)
from ansible.module_utils.orchestrator_validation.validators import (
    ib_ipv6_allocation_validator as validator,
)

pytestmark = [pytest.mark.functional, pytest.mark.unit]
LOGGER = logging.getLogger("ipv6-nm-fvt")


# ---------------------------------------------------------------------------
# Realistic multi-node allocation exports
# ---------------------------------------------------------------------------

def _dual_stack_cluster() -> dict[str, Any]:
    """5-node cluster with dual-stack IPoIB allocations."""
    allocations = []
    for i in range(1, 6):
        nid = f"nid{i:04d}"
        allocations.extend([
            {
                "allocation_id": f"alloc-v4-{i:03d}",
                "node_id": nid,
                "hostname": nid,
                "interface_id": "ib0",
                "address": f"10.0.100.{i}",
                "prefix_length": 24,
                "address_family": "ipv4",
                "fabric_id": "fabric1",
                "rail_id": "rail1",
                "rack_id": f"rack{(i-1)//10+1:02d}",
                "lifecycle_state": "active",
                "ipoib_mode": "datagram",
                "mtu": 2044,
                "pkey": "0x8001",
                "approved_prefix": "10.0.100.0/24",
                "authority": "static-ipam",
            },
            {
                "allocation_id": f"alloc-v6-{i:03d}",
                "node_id": nid,
                "hostname": nid,
                "interface_id": "ib0",
                "address": f"fd00:1b::{i}",
                "prefix_length": 64,
                "address_family": "ipv6",
                "fabric_id": "fabric1",
                "rail_id": "rail1",
                "rack_id": f"rack{(i-1)//10+1:02d}",
                "lifecycle_state": "active",
                "ipoib_mode": "datagram",
                "mtu": 2044,
                "pkey": "0x8001",
                "approved_prefix": "fd00:1b::/64",
                "authority": "static-ipam",
            },
        ])
    return {
        "schema_version": "1.0",
        "snapshot_id": "snap-fvt-cluster-001",
        "generated_at": "2026-09-26T10:00:00Z",
        "allocations": allocations,
    }


def _multi_rail_cluster() -> dict[str, Any]:
    """3-node cluster with dual-rail IPoIB (ib0 + ib1)."""
    allocations = []
    for i in range(1, 4):
        nid = f"nid{i:04d}"
        for rail_idx, (iface, prefix) in enumerate([
            ("ib0", "fd00:1b"),
            ("ib1", "fd00:2b"),
        ]):
            allocations.append({
                "allocation_id": f"alloc-{iface}-{i:03d}",
                "node_id": nid,
                "hostname": nid,
                "interface_id": iface,
                "address": f"{prefix}::{i}",
                "prefix_length": 64,
                "address_family": "ipv6",
                "fabric_id": "fabric1",
                "rail_id": f"rail{rail_idx+1}",
                "rack_id": f"rack{i:02d}",
                "lifecycle_state": "active",
                "ipoib_mode": "datagram",
                "mtu": 2044,
                "pkey": "0x8001",
                "approved_prefix": f"{prefix}::/64",
                "authority": "static-ipam",
            })
    return {
        "schema_version": "1.0",
        "snapshot_id": "snap-fvt-multirail-001",
        "generated_at": "2026-09-26T10:00:00Z",
        "allocations": allocations,
    }


# ===================================================================
# TC-FVT-009: Dual-stack interface configured via nmcli
# ===================================================================

class TestDualStackNMConfig:
    """TC-FVT-009: Dual-stack interface configured via nmcli."""

    def test_dual_stack_nmcli_profile(self):
        """ORCH_FVT_IPV6_E030: Dual-stack NM profile correctly rendered.

        Scenario: Dual-stack nmcli profile applied
          GIVEN an interface has approved IPv4 and IPv6 allocations
          WHEN the configuration script runs
          THEN one managed NM profile contains ipv4.method manual and
               ipv6.method manual and the approved addresses
        """
        data = _dual_stack_cluster()
        valid, _ = validator.preflight_validate(data, LOGGER)
        node_result = nm_renderer.render_node_full(
            "nid0001", valid["nid0001"], LOGGER
        )
        assert node_result["errors"] == []
        nm = node_result["nm_results"][0]
        assert nm["mode"] == "dual-stack"
        create_cmd = nm["commands"][1]
        assert "ipv4.method manual" in create_cmd
        assert "ipv6.method manual" in create_cmd
        assert "10.0.100.1/24" in create_cmd
        assert "fd00:1b::1/64" in create_cmd

    def test_no_ipoib_gateway(self):
        """ORCH_FVT_IPV6_E031: No IPoIB gateway or default route created.

        Scenario: No IPoIB default route created
          GIVEN any IPoIB configuration
          WHEN the configuration script completes
          THEN no IPoIB default route exists
        """
        data = _dual_stack_cluster()
        valid, _ = validator.preflight_validate(data, LOGGER)
        node_result = nm_renderer.render_node_full(
            "nid0001", valid["nid0001"], LOGGER
        )
        create_cmd = node_result["nm_results"][0]["commands"][1]
        assert "ipv4.never-default yes" in create_cmd
        assert "ipv6.never-default yes" in create_cmd

    def test_privacy_extensions_disabled(self):
        """ORCH_FVT_IPV6_E032: Privacy extensions disabled on IPoIB interface."""
        data = _dual_stack_cluster()
        valid, _ = validator.preflight_validate(data, LOGGER)
        for node_id in valid:
            node_result = nm_renderer.render_node_full(
                node_id, valid[node_id], LOGGER
            )
            for nm in node_result["nm_results"]:
                if nm["mode"] in ("dual-stack", "ipv6-only"):
                    create_cmd = nm["commands"][1]
                    assert "ipv6.ip6-privacy 0" in create_cmd, \
                        f"Privacy not disabled for {node_id}"


# ===================================================================
# TC-FVT-010: Routed input rejected
# ===================================================================

class TestRoutedInputRejected:
    """TC-FVT-010: Routed input rejected."""

    def test_gateway_in_allocation_rejected(self):
        """ORCH_FVT_IPV6_E033: Routed input rejected with specific error.

        Scenario: Routed input rejected
          GIVEN input defines an IPoIB gateway or static route
          WHEN validation runs
          THEN validation rejects the unsupported routed topology
        """
        data = _dual_stack_cluster()
        valid, _ = validator.preflight_validate(data, LOGGER)
        # Inject gateway into valid node's allocation
        ifaces = valid["nid0001"]
        for iface_id, records in ifaces.items():
            records[0]["gateway"] = "10.0.100.254"
        node_result = nm_renderer.render_node_full(
            "nid0001", ifaces, LOGGER
        )
        assert len(node_result["errors"]) >= 1
        assert any("routed" in e.lower() for e in node_result["errors"])


# ===================================================================
# TC-FVT-011: SMD receives all approved addresses
# ===================================================================

class TestSMDRegistration:
    """TC-FVT-011: SMD receives all approved addresses."""

    def test_smd_receives_both_families(self):
        """ORCH_FVT_IPV6_E034: SMD includes all applicable approved addresses.

        Scenario: SMD receives all approved addresses
          GIVEN validated allocations for selected nodes
          WHEN registration data is rendered
          THEN each logical IPoIB interface includes every applicable
               approved address in SMD
        """
        data = _dual_stack_cluster()
        valid, _ = validator.preflight_validate(data, LOGGER)
        for node_id in valid:
            result = nm_renderer.render_node_full(
                node_id, valid[node_id], LOGGER
            )
            for smd_iface in result["smd_interfaces"]:
                assert "IPV4Addresses" in smd_iface
                assert "IPV6Addresses" in smd_iface
                assert len(smd_iface["IPV4Addresses"]) >= 1
                assert len(smd_iface["IPV6Addresses"]) >= 1

    def test_smd_multi_rail(self):
        """ORCH_FVT_IPV6_E035: Multi-rail node has two SMD interface entries."""
        data = _multi_rail_cluster()
        valid, _ = validator.preflight_validate(data, LOGGER)
        result = nm_renderer.render_node_full(
            "nid0001", valid["nid0001"], LOGGER
        )
        assert len(result["smd_interfaces"]) == 2


# ===================================================================
# TC-FVT-012: Managed hosts block uses complete active snapshot
# ===================================================================

class TestManagedHostsBlock:
    """TC-FVT-012: Managed hosts block from complete active snapshot."""

    def test_all_active_nodes_present(self):
        """ORCH_FVT_IPV6_E036: All active allocations present in hosts block.

        Scenario: Managed hosts block uses complete active snapshot
          GIVEN 5 nodes in the cluster
          WHEN hostname data is rendered
          THEN entries for all 5 active nodes are present
        """
        data = _dual_stack_cluster()
        valid, _ = validator.preflight_validate(data, LOGGER)
        block = nm_renderer.render_managed_hosts_block(valid, LOGGER)
        for i in range(1, 6):
            assert f"nid{i:04d}-ib0" in block

    def test_multi_interface_hostnames_deterministic(self):
        """ORCH_FVT_IPV6_E037: Multi-interface hostnames are deterministic.

        Scenario: Multi-interface hostnames are deterministic
          GIVEN a host with ib0 and ib1
          WHEN hostname data is rendered
          THEN nid0001-ib0 and nid0001-ib1 appear as canonical entries
          AND no ambiguous short alias is generated
        """
        data = _multi_rail_cluster()
        valid, _ = validator.preflight_validate(data, LOGGER)
        block = nm_renderer.render_managed_hosts_block(valid, LOGGER)
        assert "nid0001-ib0" in block
        assert "nid0001-ib1" in block
        # Multi-interface — no -ib alias
        lines = block.split("\n")
        content_lines = [l for l in lines if "nid0001" in l]
        for line in content_lines:
            assert "nid0001-ib\t" not in line
            assert "nid0001-ib\n" not in line

    def test_hosts_block_preserves_user_content(self):
        """ORCH_FVT_IPV6_E038: Hosts block replacement preserves user content.

        Scenario: Atomic block replacement preserves user-managed content
          GIVEN existing /etc/hosts with user entries and old managed block
          WHEN the new block is applied
          THEN user entries outside the markers are preserved
          AND old managed entries are replaced
        """
        existing = (
            "127.0.0.1\tlocalhost\n"
            "10.0.0.1\toim-server\n"
            "# BEGIN Omnia IPoIB managed block\n"
            "old-addr\told-host\n"
            "# END Omnia IPoIB managed block\n"
            "192.168.1.1\tcustom-entry\n"
        )
        data = _dual_stack_cluster()
        valid, _ = validator.preflight_validate(data, LOGGER)
        new_block = nm_renderer.render_managed_hosts_block(valid, LOGGER)
        result = nm_renderer.apply_managed_hosts_block(existing, new_block)

        # User content preserved
        assert "127.0.0.1\tlocalhost" in result
        assert "10.0.0.1\toim-server" in result
        assert "192.168.1.1\tcustom-entry" in result
        # Old managed content removed
        assert "old-addr" not in result
        # New managed content present
        assert "nid0001-ib0" in result

    def test_single_interface_gets_alias(self):
        """ORCH_FVT_IPV6_E039: Single-interface nodes get hostname-ib alias."""
        data = _dual_stack_cluster()
        valid, _ = validator.preflight_validate(data, LOGGER)
        block = nm_renderer.render_managed_hosts_block(valid, LOGGER)
        # All nodes in this cluster are single-interface
        assert "nid0001-ib" in block


# ===================================================================
# TC-FVT-013: Idempotent reapplication produces no duplicates
# ===================================================================

class TestIdempotentReapplication:
    """TC-FVT-013: Idempotent reapplication produces no duplicates."""

    def test_reapplication_same_output(self):
        """ORCH_FVT_IPV6_E040: Reapplying unchanged snapshot is idempotent.

        Scenario: Idempotent reapplication produces no duplicates
          GIVEN an unchanged allocation snapshot
          WHEN provisioning is rerun
          THEN no duplicate profiles, addresses, SMD records, or host entries
        """
        data = _dual_stack_cluster()
        valid1, _ = validator.preflight_validate(data, LOGGER)
        valid2, _ = validator.preflight_validate(
            copy.deepcopy(data), LOGGER
        )

        for node_id in valid1:
            r1 = nm_renderer.render_node_full(node_id, valid1[node_id], LOGGER)
            r2 = nm_renderer.render_node_full(node_id, valid2[node_id], LOGGER)
            assert r1["config_hash"] == r2["config_hash"]
            assert not nm_renderer.is_reapplication_needed(
                r1["config_hash"], r2["config_hash"]
            )

    def test_changed_snapshot_triggers_reapplication(self):
        """ORCH_FVT_IPV6_E041: Changed snapshot triggers reapplication."""
        data1 = _dual_stack_cluster()
        data2 = copy.deepcopy(data1)
        # Change an address in the second snapshot
        data2["allocations"][1]["address"] = "fd00:1b::ff"

        valid1, _ = validator.preflight_validate(data1, LOGGER)
        valid2, _ = validator.preflight_validate(data2, LOGGER)

        r1 = nm_renderer.render_node_full("nid0001", valid1["nid0001"], LOGGER)
        r2 = nm_renderer.render_node_full("nid0001", valid2["nid0001"], LOGGER)
        assert r1["config_hash"] != r2["config_hash"]
        assert nm_renderer.is_reapplication_needed(
            r2["config_hash"], r1["config_hash"]
        )

    def test_hosts_block_idempotent(self):
        """ORCH_FVT_IPV6_E042: Double application of hosts block is idempotent."""
        data = _dual_stack_cluster()
        valid, _ = validator.preflight_validate(data, LOGGER)
        block = nm_renderer.render_managed_hosts_block(valid, LOGGER)

        existing = "127.0.0.1\tlocalhost\n"
        result1 = nm_renderer.apply_managed_hosts_block(existing, block)
        result2 = nm_renderer.apply_managed_hosts_block(result1, block)
        assert result1 == result2
