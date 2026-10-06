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
"""Unit tests for NM renderer, SMD renderer, and Hosts renderer (ER-ORCH-005).

Covers TC-UT-005 (NM Renderer), TC-UT-006 (SMD Renderer),
TC-UT-007 (Hosts Renderer) from the ER test plan.
"""

from __future__ import annotations

import logging

import pytest

from ut import source_loader  # noqa: F401
from ansible.module_utils.orchestrator_validation.renderers import (
    nm_renderer,
)

pytestmark = pytest.mark.unit
LOGGER = logging.getLogger("nm-renderer-test")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _ipv6_only_interface():
    """Single IPv6-only interface allocation."""
    return {
        "ib0": [
            {
                "allocation_id": "alloc-v6-001",
                "node_id": "nid0001",
                "hostname": "nid0001",
                "interface_id": "ib0",
                "address": "fd00:1b::1",
                "prefix_length": 64,
                "address_family": "ipv6",
                "fabric_id": "fabric1",
                "rail_id": "rail1",
                "lifecycle_state": "active",
                "ipoib_mode": "datagram",
                "mtu": 2044,
                "pkey": "0x8001",
            },
        ],
    }


def _ipv4_only_interface():
    """Single IPv4-only interface allocation."""
    return {
        "ib0": [
            {
                "allocation_id": "alloc-v4-001",
                "node_id": "nid0010",
                "hostname": "nid0010",
                "interface_id": "ib0",
                "address": "10.0.100.1",
                "prefix_length": 24,
                "address_family": "ipv4",
                "fabric_id": "fabric1",
                "rail_id": "rail1",
                "lifecycle_state": "active",
                "ipoib_mode": "datagram",
                "mtu": 2044,
                "pkey": "0x8001",
            },
        ],
    }


def _dual_stack_interface():
    """Dual-stack interface with IPv4 + IPv6."""
    return {
        "ib0": [
            {
                "allocation_id": "alloc-ds-v4",
                "node_id": "nid0002",
                "hostname": "nid0002",
                "interface_id": "ib0",
                "address": "10.0.100.2",
                "prefix_length": 24,
                "address_family": "ipv4",
                "fabric_id": "fabric1",
                "rail_id": "rail1",
                "lifecycle_state": "active",
                "ipoib_mode": "datagram",
                "mtu": 2044,
                "pkey": "0x8001",
            },
            {
                "allocation_id": "alloc-ds-v6",
                "node_id": "nid0002",
                "hostname": "nid0002",
                "interface_id": "ib0",
                "address": "fd00:1b::2",
                "prefix_length": 64,
                "address_family": "ipv6",
                "fabric_id": "fabric1",
                "rail_id": "rail1",
                "lifecycle_state": "active",
                "ipoib_mode": "datagram",
                "mtu": 2044,
                "pkey": "0x8001",
            },
        ],
    }


def _multi_interface():
    """Multi-interface node with ib0 + ib1."""
    return {
        "ib0": [
            {
                "allocation_id": "alloc-mi-ib0",
                "node_id": "nid0005",
                "hostname": "nid0005",
                "interface_id": "ib0",
                "address": "fd00:1b::5",
                "prefix_length": 64,
                "address_family": "ipv6",
                "fabric_id": "fabric1",
                "rail_id": "rail1",
                "lifecycle_state": "active",
                "ipoib_mode": "datagram",
                "mtu": 2044,
                "pkey": "0x8001",
            },
        ],
        "ib1": [
            {
                "allocation_id": "alloc-mi-ib1",
                "node_id": "nid0005",
                "hostname": "nid0005",
                "interface_id": "ib1",
                "address": "fd00:2b::5",
                "prefix_length": 64,
                "address_family": "ipv6",
                "fabric_id": "fabric1",
                "rail_id": "rail2",
                "lifecycle_state": "active",
                "ipoib_mode": "datagram",
                "mtu": 2044,
                "pkey": "0x8001",
            },
        ],
    }


# ===================================================================
# TC-UT-005: NM Renderer — nmcli command generation
# ===================================================================

class TestNMRendererCommands:
    """TC-UT-005: NM Renderer — nmcli command generation per mode."""

    def test_ipv6_only_profile(self):
        """ORCH_UT_200: IPv6-only mode generates ipv4.method disabled."""
        result = nm_renderer.render_nmcli_commands(
            "nid0001", "ib0", _ipv6_only_interface()["ib0"], LOGGER
        )
        assert result["mode"] == "ipv6-only"
        assert result["profile_name"] == "omnia-ipoib-ib0"
        create_cmd = result["commands"][1]
        assert "ipv4.method disabled" in create_cmd
        assert "ipv6.method manual" in create_cmd
        assert "fd00:1b::1/64" in create_cmd

    def test_ipv6_only_privacy_disabled(self):
        """ORCH_UT_201: IPv6-only mode disables privacy extensions."""
        result = nm_renderer.render_nmcli_commands(
            "nid0001", "ib0", _ipv6_only_interface()["ib0"], LOGGER
        )
        create_cmd = result["commands"][1]
        assert "ipv6.ip6-privacy 0" in create_cmd

    def test_ipv6_only_no_default_route(self):
        """ORCH_UT_202: IPv6-only mode sets never-default yes."""
        result = nm_renderer.render_nmcli_commands(
            "nid0001", "ib0", _ipv6_only_interface()["ib0"], LOGGER
        )
        create_cmd = result["commands"][1]
        assert "ipv6.never-default yes" in create_cmd

    def test_ipv4_only_profile(self):
        """ORCH_UT_203: IPv4-only mode generates ipv6.method link-local."""
        result = nm_renderer.render_nmcli_commands(
            "nid0010", "ib0", _ipv4_only_interface()["ib0"], LOGGER
        )
        assert result["mode"] == "ipv4-only"
        create_cmd = result["commands"][1]
        assert "ipv4.method manual" in create_cmd
        assert "ipv6.method link-local" in create_cmd
        assert "10.0.100.1/24" in create_cmd

    def test_dual_stack_profile(self):
        """ORCH_UT_204: Dual-stack has both ipv4.method manual and ipv6.method manual."""
        result = nm_renderer.render_nmcli_commands(
            "nid0002", "ib0", _dual_stack_interface()["ib0"], LOGGER
        )
        assert result["mode"] == "dual-stack"
        create_cmd = result["commands"][1]
        assert "ipv4.method manual" in create_cmd
        assert "ipv6.method manual" in create_cmd
        assert "10.0.100.2/24" in create_cmd
        assert "fd00:1b::2/64" in create_cmd

    def test_dual_stack_no_gateway(self):
        """ORCH_UT_205: Dual-stack does not set any gateway."""
        result = nm_renderer.render_nmcli_commands(
            "nid0002", "ib0", _dual_stack_interface()["ib0"], LOGGER
        )
        create_cmd = result["commands"][1]
        assert "ipv4.never-default yes" in create_cmd
        assert "ipv6.never-default yes" in create_cmd
        assert "gateway" not in create_cmd.lower() or \
            "never-default" in create_cmd

    def test_delete_before_create(self):
        """ORCH_UT_206: Delete command precedes create for idempotency."""
        result = nm_renderer.render_nmcli_commands(
            "nid0001", "ib0", _ipv6_only_interface()["ib0"], LOGGER
        )
        assert len(result["commands"]) >= 3
        assert "delete" in result["commands"][0]
        assert "con add" in result["commands"][1]
        assert "con up" in result["commands"][2]

    def test_mtu_applied(self):
        """ORCH_UT_207: MTU is applied to the profile."""
        result = nm_renderer.render_nmcli_commands(
            "nid0001", "ib0", _ipv6_only_interface()["ib0"], LOGGER
        )
        create_cmd = result["commands"][1]
        assert "infiniband.mtu 2044" in create_cmd

    def test_multi_interface_produces_two_results(self):
        """ORCH_UT_208: Multi-interface node produces two render results."""
        results = nm_renderer.render_node_nmcli(
            "nid0005", _multi_interface(), LOGGER
        )
        assert len(results) == 2
        profiles = {r["profile_name"] for r in results}
        assert "omnia-ipoib-ib0" in profiles
        assert "omnia-ipoib-ib1" in profiles


class TestRoutedInputRejection:
    """NM Renderer — routed input rejection (FR-3, AC-002)."""

    def test_gateway_rejected(self):
        """ORCH_UT_210: Allocation with gateway is rejected."""
        record = _ipv6_only_interface()["ib0"][0].copy()
        record["gateway"] = "fd00:1b::ffff"
        errors = nm_renderer.reject_routed_input(record, LOGGER)
        assert len(errors) == 1
        assert "gateway" in errors[0].lower()

    def test_static_routes_rejected(self):
        """ORCH_UT_211: Allocation with static_routes is rejected."""
        record = _ipv6_only_interface()["ib0"][0].copy()
        record["static_routes"] = [{"dest": "fd00:ff::/48"}]
        errors = nm_renderer.reject_routed_input(record, LOGGER)
        assert len(errors) == 1

    def test_clean_allocation_passes(self):
        """ORCH_UT_212: Clean allocation without routed input passes."""
        record = _ipv6_only_interface()["ib0"][0]
        errors = nm_renderer.reject_routed_input(record, LOGGER)
        assert errors == []

    def test_routed_interface_produces_error_result(self):
        """ORCH_UT_213: Routed interface renders as error result."""
        ifaces = _ipv6_only_interface()
        ifaces["ib0"][0]["gateway"] = "fd00:1b::ffff"
        results = nm_renderer.render_node_nmcli("nid0001", ifaces, LOGGER)
        assert results[0]["mode"] == "error"
        assert len(results[0]["errors"]) >= 1


# ===================================================================
# TC-UT-005 (cont.): Cloud-init rendering
# ===================================================================

class TestCloudInitRendering:
    """Cloud-init user-data rendering for nmcli script delivery."""

    def test_script_generated(self):
        """ORCH_UT_220: Cloud-init script generated with write_files + runcmd."""
        nm_results = nm_renderer.render_node_nmcli(
            "nid0001", _ipv6_only_interface(), LOGGER
        )
        ci = nm_renderer.render_cloud_init_script("nid0001", nm_results)
        assert "write_files" in ci
        assert "runcmd" in ci
        assert len(ci["write_files"]) == 1
        assert ci["write_files"][0]["permissions"] == "0755"
        assert "nid0001" in ci["write_files"][0]["path"]

    def test_script_contains_nmcli_commands(self):
        """ORCH_UT_221: Cloud-init script content includes nmcli commands."""
        nm_results = nm_renderer.render_node_nmcli(
            "nid0001", _ipv6_only_interface(), LOGGER
        )
        ci = nm_renderer.render_cloud_init_script("nid0001", nm_results)
        content = ci["write_files"][0]["content"]
        assert "nmcli con add" in content
        assert "nmcli con up" in content
        assert "#!/bin/bash" in content

    def test_multi_interface_script(self):
        """ORCH_UT_222: Multi-interface node generates multi-interface script."""
        nm_results = nm_renderer.render_node_nmcli(
            "nid0005", _multi_interface(), LOGGER
        )
        ci = nm_renderer.render_cloud_init_script("nid0005", nm_results)
        content = ci["write_files"][0]["content"]
        assert "ib0" in content
        assert "ib1" in content


# ===================================================================
# TC-UT-006: SMD Renderer — component/interface payload generation
# ===================================================================

class TestSMDRenderer:
    """TC-UT-006: SMD Renderer — component/interface payload generation."""

    def test_single_ipv6_interface(self):
        """ORCH_UT_230: Single IPv6 interface produces correct SMD payload."""
        ifaces = nm_renderer.render_smd_interfaces(
            "nid0001", _ipv6_only_interface(), LOGGER
        )
        assert len(ifaces) == 1
        assert ifaces[0]["ID"] == "nid0001-ib0"
        assert ifaces[0]["ComponentID"] == "nid0001"
        assert "IPV6Addresses" in ifaces[0]
        assert len(ifaces[0]["IPV6Addresses"]) == 1
        assert ifaces[0]["IPV6Addresses"][0]["IPAddress"] == "fd00:1b::1"

    def test_dual_stack_interface(self):
        """ORCH_UT_231: Dual-stack interface has both IPv4 and IPv6 in SMD."""
        ifaces = nm_renderer.render_smd_interfaces(
            "nid0002", _dual_stack_interface(), LOGGER
        )
        assert len(ifaces) == 1
        assert "IPV4Addresses" in ifaces[0]
        assert "IPV6Addresses" in ifaces[0]
        assert ifaces[0]["IPV4Addresses"][0]["IPAddress"] == "10.0.100.2"
        assert ifaces[0]["IPV6Addresses"][0]["IPAddress"] == "fd00:1b::2"

    def test_multi_interface_produces_two_smd_entries(self):
        """ORCH_UT_232: Multi-interface node produces two SMD interface entries."""
        ifaces = nm_renderer.render_smd_interfaces(
            "nid0005", _multi_interface(), LOGGER
        )
        assert len(ifaces) == 2
        ids = {i["ID"] for i in ifaces}
        assert "nid0005-ib0" in ids
        assert "nid0005-ib1" in ids

    def test_smd_component_payload(self):
        """ORCH_UT_233: SMD component payload includes hostname and interfaces."""
        comp = nm_renderer.render_smd_component(
            "nid0001", "nid0001", _ipv6_only_interface(), LOGGER
        )
        assert comp["ID"] == "nid0001"
        assert comp["Hostname"] == "nid0001"
        assert comp["NetType"] == "InfiniBand"
        assert len(comp["Interfaces"]) == 1

    def test_ipv4_only_smd_no_ipv6(self):
        """ORCH_UT_234: IPv4-only interface has no IPV6Addresses in SMD."""
        ifaces = nm_renderer.render_smd_interfaces(
            "nid0010", _ipv4_only_interface(), LOGGER
        )
        assert "IPV4Addresses" in ifaces[0]
        assert "IPV6Addresses" not in ifaces[0]


# ===================================================================
# TC-UT-007: Hosts Renderer — managed /etc/hosts block
# ===================================================================

class TestHostsRenderer:
    """TC-UT-007: Hosts Renderer — managed /etc/hosts block."""

    def test_single_interface_hostname(self):
        """ORCH_UT_240: Single-interface node gets canonical + alias."""
        record = _ipv6_only_interface()["ib0"][0]
        entry = nm_renderer.render_hostname_entry(record, is_single_interface=True)
        assert "nid0001-ib0" in entry
        assert "nid0001-ib" in entry
        assert "fd00:1b::1" in entry

    def test_multi_interface_no_alias(self):
        """ORCH_UT_241: Multi-interface node gets canonical only, no -ib alias."""
        record = _multi_interface()["ib0"][0]
        entry = nm_renderer.render_hostname_entry(record, is_single_interface=False)
        assert "nid0005-ib0" in entry
        assert "nid0005-ib\t" not in entry
        assert "nid0005-ib\n" not in entry

    def test_managed_block_contains_markers(self):
        """ORCH_UT_242: Managed block has BEGIN and END markers."""
        nodes = {
            "nid0001": _ipv6_only_interface(),
        }
        block = nm_renderer.render_managed_hosts_block(nodes, LOGGER)
        assert nm_renderer.HOSTS_BEGIN_MARKER in block
        assert nm_renderer.HOSTS_END_MARKER in block

    def test_managed_block_multi_node(self):
        """ORCH_UT_243: Block contains entries for all nodes."""
        nodes = {
            "nid0001": _ipv6_only_interface(),
            "nid0005": _multi_interface(),
        }
        block = nm_renderer.render_managed_hosts_block(nodes, LOGGER)
        assert "nid0001-ib0" in block
        assert "nid0005-ib0" in block
        assert "nid0005-ib1" in block

    def test_managed_block_sorted_by_node(self):
        """ORCH_UT_244: Block entries are sorted by node ID."""
        nodes = {
            "nid0005": _multi_interface(),
            "nid0001": _ipv6_only_interface(),
        }
        block = nm_renderer.render_managed_hosts_block(nodes, LOGGER)
        lines = block.split("\n")
        # After marker, nid0001 should come before nid0005
        content_lines = [l for l in lines if l and not l.startswith("#")]
        assert "nid0001" in content_lines[0]

    def test_apply_replaces_existing_block(self):
        """ORCH_UT_245: apply_managed_hosts_block replaces existing markers."""
        existing = (
            "127.0.0.1\tlocalhost\n"
            "# BEGIN Omnia IPoIB managed block\n"
            "old-entry\told-host\n"
            "# END Omnia IPoIB managed block\n"
            "::1\tlocalhost6\n"
        )
        new_block = nm_renderer.render_managed_hosts_block(
            {"nid0001": _ipv6_only_interface()}, LOGGER
        )
        result = nm_renderer.apply_managed_hosts_block(existing, new_block)
        assert "old-entry" not in result
        assert "nid0001-ib0" in result
        assert "127.0.0.1" in result
        assert "::1\tlocalhost6" in result

    def test_apply_appends_when_no_markers(self):
        """ORCH_UT_246: apply_managed_hosts_block appends when no markers exist."""
        existing = "127.0.0.1\tlocalhost\n"
        new_block = nm_renderer.render_managed_hosts_block(
            {"nid0001": _ipv6_only_interface()}, LOGGER
        )
        result = nm_renderer.apply_managed_hosts_block(existing, new_block)
        assert result.startswith("127.0.0.1")
        assert "nid0001-ib0" in result
        assert nm_renderer.HOSTS_BEGIN_MARKER in result


# ===================================================================
# Idempotent reapplication (AC-006)
# ===================================================================

class TestIdempotentReapplication:
    """Idempotent reapplication detection via config hash."""

    def test_same_config_same_hash(self):
        """ORCH_UT_250: Same configuration produces same hash."""
        nm1 = nm_renderer.render_node_nmcli(
            "nid0001", _ipv6_only_interface(), LOGGER
        )
        nm2 = nm_renderer.render_node_nmcli(
            "nid0001", _ipv6_only_interface(), LOGGER
        )
        assert nm_renderer.compute_config_hash(nm1) == \
            nm_renderer.compute_config_hash(nm2)

    def test_different_config_different_hash(self):
        """ORCH_UT_251: Different configuration produces different hash."""
        nm_v6 = nm_renderer.render_node_nmcli(
            "nid0001", _ipv6_only_interface(), LOGGER
        )
        nm_v4 = nm_renderer.render_node_nmcli(
            "nid0010", _ipv4_only_interface(), LOGGER
        )
        assert nm_renderer.compute_config_hash(nm_v6) != \
            nm_renderer.compute_config_hash(nm_v4)

    def test_first_run_needs_application(self):
        """ORCH_UT_252: First run (no previous hash) needs application."""
        assert nm_renderer.is_reapplication_needed("abc123", None) is True

    def test_unchanged_config_no_reapplication(self):
        """ORCH_UT_253: Unchanged config skips reapplication."""
        assert nm_renderer.is_reapplication_needed("abc", "abc") is False

    def test_changed_config_needs_reapplication(self):
        """ORCH_UT_254: Changed config triggers reapplication."""
        assert nm_renderer.is_reapplication_needed("abc", "def") is True


# ===================================================================
# Full pipeline
# ===================================================================

class TestFullPipeline:
    """Full render_node_full pipeline integration."""

    def test_full_pipeline_ipv6_only(self):
        """ORCH_UT_260: Full pipeline produces all artifacts for IPv6-only node."""
        result = nm_renderer.render_node_full(
            "nid0001", _ipv6_only_interface(), LOGGER
        )
        assert result["node_id"] == "nid0001"
        assert result["hostname"] == "nid0001"
        assert len(result["nm_results"]) == 1
        assert "write_files" in result["cloud_init"]
        assert len(result["smd_interfaces"]) == 1
        assert result["config_hash"]
        assert result["errors"] == []

    def test_full_pipeline_multi_interface(self):
        """ORCH_UT_261: Full pipeline for multi-interface node."""
        result = nm_renderer.render_node_full(
            "nid0005", _multi_interface(), LOGGER
        )
        assert len(result["nm_results"]) == 2
        assert len(result["smd_interfaces"]) == 2
