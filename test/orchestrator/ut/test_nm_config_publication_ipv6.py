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
"""Portable unit tests for NM config, SMD renderer, and hosts publication.

Story: ER-ORCH-005-nm-config-publication
Supplements test_nm_renderer.py (which requires Unix source_loader).

Covers:
- TC-UT-005: NM Renderer — nmcli command generation per mode (edge cases)
- TC-UT-006: SMD Renderer — component/interface payload (edge cases)
- TC-UT-007: Hosts Renderer — managed /etc/hosts block (edge cases)
- TC-FVT-009: Dual-stack, IPv6-only, IPv4-only NM profiles
- TC-FVT-010: Routed input rejection
- TC-FVT-012: Managed hosts block completeness
- TC-FVT-013: Idempotent reapplication
- Jinja2 template backward compatibility verification
- Security: no credentials in generated artifacts

These tests import nm_renderer directly via sys.path
without requiring fcntl or source_loader.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from unittest import mock

import pytest

# Set up module path to import nm_renderer without source_loader/fcntl
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PLUGINS_DIR = _REPO_ROOT / "src" / "orchestrator" / "plugins"
sys.path.insert(0, str(_PLUGINS_DIR / "module_utils"))
sys.path.insert(0, str(_PLUGINS_DIR))

# Mock ansible.module_utils to allow import without ansible installed
sys.modules.setdefault("ansible", mock.MagicMock())
sys.modules.setdefault("ansible.module_utils", mock.MagicMock())
sys.modules.setdefault("ansible.module_utils.basic", mock.MagicMock())

from orchestrator_validation.renderers import nm_renderer  # noqa: E402

pytestmark = pytest.mark.unit
LOGGER = logging.getLogger("nm-config-pub-test")

# Path to the Jinja2 template for backward compatibility checks
_TEMPLATE_PATH = (
    _REPO_ROOT / "src" / "orchestrator" / "roles" / "configure_ochami"
    / "templates" / "doca-ofed" / "configure-ib-network.sh.j2"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _ipv6_only():
    """Single IPv6-only interface allocation."""
    return {
        "ib0": [{
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
        }],
    }


def _ipv4_only():
    """Single IPv4-only interface allocation."""
    return {
        "ib0": [{
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
        }],
    }


def _dual_stack():
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
        "ib0": [{
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
        }],
        "ib1": [{
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
        }],
    }


# ===================================================================
# TC-UT-005: NM Renderer — nmcli mode-specific rendering
# ===================================================================

class TestNMRendererModes:
    """TC-UT-005: NM Renderer — mode-specific nmcli command generation."""

    def test_ipv6_only_ipv4_disabled(self):
        """ORCH_UT_NM_001: IPv6-only mode disables IPv4."""
        result = nm_renderer.render_nmcli_commands(
            "nid0001", "ib0", _ipv6_only()["ib0"], LOGGER
        )
        assert result["mode"] == "ipv6-only"
        create_cmd = result["commands"][1]
        assert "ipv4.method disabled" in create_cmd
        assert "ipv6.method manual" in create_cmd

    def test_ipv4_only_ipv6_linklocal(self):
        """ORCH_UT_NM_002: IPv4-only mode sets IPv6 to link-local."""
        result = nm_renderer.render_nmcli_commands(
            "nid0010", "ib0", _ipv4_only()["ib0"], LOGGER
        )
        assert result["mode"] == "ipv4-only"
        create_cmd = result["commands"][1]
        assert "ipv6.method link-local" in create_cmd

    def test_dual_stack_both_manual(self):
        """ORCH_UT_NM_003: Dual-stack has both methods manual."""
        result = nm_renderer.render_nmcli_commands(
            "nid0002", "ib0", _dual_stack()["ib0"], LOGGER
        )
        assert result["mode"] == "dual-stack"
        create_cmd = result["commands"][1]
        assert "ipv4.method manual" in create_cmd
        assert "ipv6.method manual" in create_cmd

    def test_addresses_present_in_commands(self):
        """ORCH_UT_NM_004: All allocated addresses appear in nmcli commands."""
        result = nm_renderer.render_nmcli_commands(
            "nid0002", "ib0", _dual_stack()["ib0"], LOGGER
        )
        create_cmd = result["commands"][1]
        assert "10.0.100.2/24" in create_cmd
        assert "fd00:1b::2/64" in create_cmd


# ===================================================================
# TC-UT-005: Privacy and route constraints
# ===================================================================

class TestPrivacyAndRouteConstraints:
    """Privacy extensions disabled and no default route (FR-3, AC-002)."""

    def test_privacy_disabled_ipv6_only(self):
        """ORCH_UT_NM_010: IPv6-only disables privacy extensions."""
        result = nm_renderer.render_nmcli_commands(
            "nid0001", "ib0", _ipv6_only()["ib0"], LOGGER
        )
        create_cmd = result["commands"][1]
        assert "ipv6.ip6-privacy 0" in create_cmd

    def test_privacy_disabled_dual_stack(self):
        """ORCH_UT_NM_011: Dual-stack disables privacy extensions."""
        result = nm_renderer.render_nmcli_commands(
            "nid0002", "ib0", _dual_stack()["ib0"], LOGGER
        )
        create_cmd = result["commands"][1]
        assert "ipv6.ip6-privacy 0" in create_cmd

    def test_never_default_ipv6(self):
        """ORCH_UT_NM_012: IPv6 never-default set on IPv6 modes."""
        result = nm_renderer.render_nmcli_commands(
            "nid0001", "ib0", _ipv6_only()["ib0"], LOGGER
        )
        create_cmd = result["commands"][1]
        assert "ipv6.never-default yes" in create_cmd

    def test_never_default_both_stacks(self):
        """ORCH_UT_NM_013: Both ipv4 and ipv6 never-default in dual-stack."""
        result = nm_renderer.render_nmcli_commands(
            "nid0002", "ib0", _dual_stack()["ib0"], LOGGER
        )
        create_cmd = result["commands"][1]
        assert "ipv4.never-default yes" in create_cmd
        assert "ipv6.never-default yes" in create_cmd

    def test_no_gateway_in_any_mode(self):
        """ORCH_UT_NM_014: No gateway keyword (except never-default) in commands."""
        for fixture, node_id in [(_ipv6_only, "nid0001"),
                                 (_ipv4_only, "nid0010"),
                                 (_dual_stack, "nid0002")]:
            ifaces = fixture()
            results = nm_renderer.render_node_nmcli(node_id, ifaces, LOGGER)
            for result in results:
                if result.get("mode") == "error":
                    continue
                for cmd in result["commands"]:
                    # "gateway" should only appear in "never-default"
                    gw_matches = re.findall(r"gateway", cmd, re.IGNORECASE)
                    nd_matches = re.findall(r"never-default", cmd)
                    assert len(gw_matches) <= len(nd_matches), (
                        f"Gateway found without never-default in: {cmd}"
                    )


# ===================================================================
# TC-FVT-010: Routed input rejection
# ===================================================================

class TestRoutedInputRejection:
    """TC-FVT-010: Routed input rejected for all routed key variants."""

    @pytest.mark.parametrize("routed_key,value", [
        ("gateway", "fd00:1b::ffff"),
        ("gateway4", "10.0.100.254"),
        ("gateway6", "fd00:1b::ffff"),
        ("ipv4_gateway", "10.0.100.254"),
        ("ipv6_gateway", "fd00:1b::ffff"),
        ("static_routes", [{"dest": "fd00:ff::/48"}]),
        ("routes", [{"dest": "::/0"}]),
    ])
    def test_all_routed_keys_rejected(self, routed_key, value):
        """ORCH_UT_NM_020: Each routed key variant is rejected."""
        record = _ipv6_only()["ib0"][0].copy()
        record[routed_key] = value
        errors = nm_renderer.reject_routed_input(record, LOGGER)
        assert len(errors) >= 1
        assert any(routed_key in e for e in errors)

    def test_clean_record_passes(self):
        """ORCH_UT_NM_021: Clean record without routed keys passes."""
        record = _ipv6_only()["ib0"][0]
        errors = nm_renderer.reject_routed_input(record, LOGGER)
        assert errors == []


# ===================================================================
# TC-UT-005: Command sequence and idempotency
# ===================================================================

class TestCommandSequenceIdempotency:
    """Idempotent command sequence: delete → create → up."""

    def test_delete_before_create(self):
        """ORCH_UT_NM_030: Delete precedes create for idempotency."""
        result = nm_renderer.render_nmcli_commands(
            "nid0001", "ib0", _ipv6_only()["ib0"], LOGGER
        )
        assert len(result["commands"]) >= 3
        assert "delete" in result["commands"][0]
        assert "con add" in result["commands"][1]
        assert "con up" in result["commands"][2]

    def test_profile_name_convention(self):
        """ORCH_UT_NM_031: Profile name follows omnia-ipoib-<iface> convention."""
        result = nm_renderer.render_nmcli_commands(
            "nid0001", "ib0", _ipv6_only()["ib0"], LOGGER
        )
        assert result["profile_name"] == "omnia-ipoib-ib0"

    def test_mtu_applied(self):
        """ORCH_UT_NM_032: MTU value applied in create command."""
        result = nm_renderer.render_nmcli_commands(
            "nid0001", "ib0", _ipv6_only()["ib0"], LOGGER
        )
        create_cmd = result["commands"][1]
        assert "infiniband.mtu 2044" in create_cmd

    def test_autoconnect_yes(self):
        """ORCH_UT_NM_033: Autoconnect enabled."""
        result = nm_renderer.render_nmcli_commands(
            "nid0001", "ib0", _ipv6_only()["ib0"], LOGGER
        )
        create_cmd = result["commands"][1]
        assert "connection.autoconnect yes" in create_cmd

    def test_ipoib_transport_mode(self):
        """ORCH_UT_NM_034: IPoIB transport mode set in create command."""
        result = nm_renderer.render_nmcli_commands(
            "nid0001", "ib0", _ipv6_only()["ib0"], LOGGER
        )
        create_cmd = result["commands"][1]
        assert "infiniband.transport-mode datagram" in create_cmd


# ===================================================================
# TC-UT-005: Cloud-init rendering
# ===================================================================

class TestCloudInitRendering:
    """Cloud-init user-data rendering."""

    def test_script_has_write_files_and_runcmd(self):
        """ORCH_UT_NM_040: Cloud-init structure has write_files + runcmd."""
        nm_results = nm_renderer.render_node_nmcli(
            "nid0001", _ipv6_only(), LOGGER
        )
        ci = nm_renderer.render_cloud_init_script("nid0001", nm_results)
        assert "write_files" in ci
        assert "runcmd" in ci
        assert len(ci["write_files"]) == 1

    def test_script_has_bash_shebang(self):
        """ORCH_UT_NM_041: Script starts with bash shebang."""
        nm_results = nm_renderer.render_node_nmcli(
            "nid0001", _ipv6_only(), LOGGER
        )
        ci = nm_renderer.render_cloud_init_script("nid0001", nm_results)
        content = ci["write_files"][0]["content"]
        assert content.startswith("#!/bin/bash")

    def test_script_has_strict_mode(self):
        """ORCH_UT_NM_042: Script uses set -euo pipefail."""
        nm_results = nm_renderer.render_node_nmcli(
            "nid0001", _ipv6_only(), LOGGER
        )
        ci = nm_renderer.render_cloud_init_script("nid0001", nm_results)
        content = ci["write_files"][0]["content"]
        assert "set -euo pipefail" in content

    def test_script_permissions(self):
        """ORCH_UT_NM_043: Script is executable (0755)."""
        nm_results = nm_renderer.render_node_nmcli(
            "nid0001", _ipv6_only(), LOGGER
        )
        ci = nm_renderer.render_cloud_init_script("nid0001", nm_results)
        assert ci["write_files"][0]["permissions"] == "0755"

    def test_multi_interface_script_covers_both(self):
        """ORCH_UT_NM_044: Multi-interface script references both interfaces."""
        nm_results = nm_renderer.render_node_nmcli(
            "nid0005", _multi_interface(), LOGGER
        )
        ci = nm_renderer.render_cloud_init_script("nid0005", nm_results)
        content = ci["write_files"][0]["content"]
        assert "ib0" in content
        assert "ib1" in content


# ===================================================================
# TC-UT-006: SMD Renderer
# ===================================================================

class TestSMDRenderer:
    """TC-UT-006: SMD Renderer — component/interface payload generation."""

    def test_ipv6_only_has_ipv6_addresses(self):
        """ORCH_UT_NM_050: IPv6-only interface produces IPV6Addresses."""
        ifaces = nm_renderer.render_smd_interfaces(
            "nid0001", _ipv6_only(), LOGGER
        )
        assert len(ifaces) == 1
        assert "IPV6Addresses" in ifaces[0]
        assert ifaces[0]["IPV6Addresses"][0]["IPAddress"] == "fd00:1b::1"

    def test_ipv4_only_has_no_ipv6(self):
        """ORCH_UT_NM_051: IPv4-only interface has no IPV6Addresses key."""
        ifaces = nm_renderer.render_smd_interfaces(
            "nid0010", _ipv4_only(), LOGGER
        )
        assert "IPV4Addresses" in ifaces[0]
        assert "IPV6Addresses" not in ifaces[0]

    def test_dual_stack_has_both_families(self):
        """ORCH_UT_NM_052: Dual-stack has both IPV4 and IPV6 addresses."""
        ifaces = nm_renderer.render_smd_interfaces(
            "nid0002", _dual_stack(), LOGGER
        )
        assert "IPV4Addresses" in ifaces[0]
        assert "IPV6Addresses" in ifaces[0]

    def test_smd_interface_id_format(self):
        """ORCH_UT_NM_053: SMD interface ID is <node_id>-<iface_id>."""
        ifaces = nm_renderer.render_smd_interfaces(
            "nid0001", _ipv6_only(), LOGGER
        )
        assert ifaces[0]["ID"] == "nid0001-ib0"
        assert ifaces[0]["ComponentID"] == "nid0001"

    def test_smd_component_payload_structure(self):
        """ORCH_UT_NM_054: SMD component payload has required fields."""
        comp = nm_renderer.render_smd_component(
            "nid0001", "nid0001", _ipv6_only(), LOGGER
        )
        assert comp["ID"] == "nid0001"
        assert comp["Hostname"] == "nid0001"
        assert comp["NetType"] == "InfiniBand"
        assert len(comp["Interfaces"]) == 1

    def test_multi_interface_produces_two_smd_entries(self):
        """ORCH_UT_NM_055: Multi-interface node produces 2 SMD entries."""
        ifaces = nm_renderer.render_smd_interfaces(
            "nid0005", _multi_interface(), LOGGER
        )
        assert len(ifaces) == 2
        ids = {i["ID"] for i in ifaces}
        assert "nid0005-ib0" in ids
        assert "nid0005-ib1" in ids


# ===================================================================
# TC-UT-007: Hosts Renderer
# ===================================================================

class TestHostsRenderer:
    """TC-UT-007: Managed /etc/hosts block rendering."""

    def test_single_interface_gets_alias(self):
        """ORCH_UT_NM_060: Single-interface gets canonical + alias."""
        record = _ipv6_only()["ib0"][0]
        entry = nm_renderer.render_hostname_entry(record, is_single_interface=True)
        assert "nid0001-ib0" in entry
        assert "nid0001-ib" in entry

    def test_multi_interface_no_alias(self):
        """ORCH_UT_NM_061: Multi-interface has canonical only, no -ib alias."""
        record = _multi_interface()["ib0"][0]
        entry = nm_renderer.render_hostname_entry(record, is_single_interface=False)
        assert "nid0005-ib0" in entry
        # No bare -ib alias
        parts = entry.split("\t")
        assert not any(p == "nid0005-ib" for p in parts)

    def test_block_markers_present(self):
        """ORCH_UT_NM_062: Managed block has BEGIN and END markers."""
        nodes = {"nid0001": _ipv6_only()}
        block = nm_renderer.render_managed_hosts_block(nodes, LOGGER)
        assert nm_renderer.HOSTS_BEGIN_MARKER in block
        assert nm_renderer.HOSTS_END_MARKER in block

    def test_block_sorted_by_node_id(self):
        """ORCH_UT_NM_063: Entries sorted by node ID."""
        nodes = {
            "nid0005": _multi_interface(),
            "nid0001": _ipv6_only(),
        }
        block = nm_renderer.render_managed_hosts_block(nodes, LOGGER)
        lines = [l for l in block.split("\n")
                 if l and not l.startswith("#")]
        assert "nid0001" in lines[0]

    def test_apply_replaces_existing_block(self):
        """ORCH_UT_NM_064: Apply replaces old block, preserves user content."""
        existing = (
            "127.0.0.1\tlocalhost\n"
            "# BEGIN Omnia IPoIB managed block\n"
            "old-entry\told-host\n"
            "# END Omnia IPoIB managed block\n"
            "::1\tlocalhost6\n"
        )
        new_block = nm_renderer.render_managed_hosts_block(
            {"nid0001": _ipv6_only()}, LOGGER
        )
        result = nm_renderer.apply_managed_hosts_block(existing, new_block)
        assert "old-entry" not in result
        assert "nid0001-ib0" in result
        assert "127.0.0.1" in result
        assert "::1\tlocalhost6" in result

    def test_apply_appends_when_no_markers(self):
        """ORCH_UT_NM_065: Apply appends when no existing markers."""
        existing = "127.0.0.1\tlocalhost\n"
        new_block = nm_renderer.render_managed_hosts_block(
            {"nid0001": _ipv6_only()}, LOGGER
        )
        result = nm_renderer.apply_managed_hosts_block(existing, new_block)
        assert result.startswith("127.0.0.1")
        assert "nid0001-ib0" in result

    def test_double_apply_idempotent(self):
        """ORCH_UT_NM_066: Double application is idempotent."""
        existing = "127.0.0.1\tlocalhost\n"
        block = nm_renderer.render_managed_hosts_block(
            {"nid0001": _ipv6_only()}, LOGGER
        )
        r1 = nm_renderer.apply_managed_hosts_block(existing, block)
        r2 = nm_renderer.apply_managed_hosts_block(r1, block)
        assert r1 == r2


# ===================================================================
# TC-FVT-013: Idempotent reapplication via config hash
# ===================================================================

class TestIdempotentReapplication:
    """TC-FVT-013: Idempotent reapplication detection."""

    def test_same_config_same_hash(self):
        """ORCH_UT_NM_070: Same config produces same hash."""
        nm1 = nm_renderer.render_node_nmcli("nid0001", _ipv6_only(), LOGGER)
        nm2 = nm_renderer.render_node_nmcli("nid0001", _ipv6_only(), LOGGER)
        assert nm_renderer.compute_config_hash(nm1) == \
            nm_renderer.compute_config_hash(nm2)

    def test_different_config_different_hash(self):
        """ORCH_UT_NM_071: Different config produces different hash."""
        nm_v6 = nm_renderer.render_node_nmcli("nid0001", _ipv6_only(), LOGGER)
        nm_v4 = nm_renderer.render_node_nmcli("nid0010", _ipv4_only(), LOGGER)
        assert nm_renderer.compute_config_hash(nm_v6) != \
            nm_renderer.compute_config_hash(nm_v4)

    def test_first_run_needs_application(self):
        """ORCH_UT_NM_072: First run (no previous hash) needs application."""
        assert nm_renderer.is_reapplication_needed("abc123", None) is True

    def test_unchanged_no_reapplication(self):
        """ORCH_UT_NM_073: Unchanged config skips reapplication."""
        assert nm_renderer.is_reapplication_needed("abc", "abc") is False

    def test_changed_needs_reapplication(self):
        """ORCH_UT_NM_074: Changed config triggers reapplication."""
        assert nm_renderer.is_reapplication_needed("abc", "def") is True


# ===================================================================
# Full pipeline
# ===================================================================

class TestFullPipeline:
    """Full render_node_full pipeline integration."""

    def test_full_pipeline_produces_all_artifacts(self):
        """ORCH_UT_NM_080: Full pipeline produces nm, cloud-init, SMD, hash."""
        result = nm_renderer.render_node_full(
            "nid0001", _ipv6_only(), LOGGER
        )
        assert result["node_id"] == "nid0001"
        assert result["hostname"] == "nid0001"
        assert len(result["nm_results"]) == 1
        assert "write_files" in result["cloud_init"]
        assert len(result["smd_interfaces"]) == 1
        assert result["config_hash"]
        assert result["errors"] == []

    def test_full_pipeline_multi_interface(self):
        """ORCH_UT_NM_081: Full pipeline for multi-interface node."""
        result = nm_renderer.render_node_full(
            "nid0005", _multi_interface(), LOGGER
        )
        assert len(result["nm_results"]) == 2
        assert len(result["smd_interfaces"]) == 2

    def test_full_pipeline_routed_error(self):
        """ORCH_UT_NM_082: Gateway in allocation causes error in full pipeline."""
        ifaces = _ipv6_only()
        ifaces["ib0"][0]["gateway"] = "fd00:1b::ffff"
        result = nm_renderer.render_node_full("nid0001", ifaces, LOGGER)
        assert len(result["errors"]) >= 1


# ===================================================================
# Security: No credentials in generated artifacts
# ===================================================================

class TestNoCredentials:
    """Security: generated artifacts contain no credentials."""

    _CREDENTIAL_PATTERNS = [
        "password", "secret", "token", "Bearer ",
        "ssh-rsa ", "BEGIN PRIVATE", "vault_password",
        "ansible_ssh_pass",
    ]

    def test_nmcli_commands_no_credentials(self):
        """ORCH_UT_NM_090: nmcli commands contain no credential patterns."""
        for fixture, node in [(_ipv6_only, "nid0001"),
                              (_dual_stack, "nid0002")]:
            ifaces = fixture()
            results = nm_renderer.render_node_nmcli(node, ifaces, LOGGER)
            for result in results:
                for cmd in result.get("commands", []):
                    for pattern in self._CREDENTIAL_PATTERNS:
                        assert pattern not in cmd, (
                            f"Credential pattern '{pattern}' in command"
                        )

    def test_cloud_init_script_no_credentials(self):
        """ORCH_UT_NM_091: Cloud-init script contains no credential patterns."""
        nm_results = nm_renderer.render_node_nmcli(
            "nid0001", _ipv6_only(), LOGGER
        )
        ci = nm_renderer.render_cloud_init_script("nid0001", nm_results)
        content = ci["write_files"][0]["content"]
        for pattern in self._CREDENTIAL_PATTERNS:
            assert pattern not in content

    def test_hosts_block_no_credentials(self):
        """ORCH_UT_NM_092: Hosts block contains no credential patterns."""
        block = nm_renderer.render_managed_hosts_block(
            {"nid0001": _ipv6_only()}, LOGGER
        )
        for pattern in self._CREDENTIAL_PATTERNS:
            assert pattern not in block


# ===================================================================
# Jinja2 template backward compatibility
# ===================================================================

class TestJinja2TemplateBackwardCompat:
    """Jinja2 template backward compat: legacy IB_IP and IPv6 additions."""

    @pytest.fixture(autouse=True)
    def _load_template(self):
        """Load the Jinja2 template content."""
        if not _TEMPLATE_PATH.exists():
            pytest.skip("Jinja2 template not found")
        self.template = _TEMPLATE_PATH.read_text(encoding="utf-8")

    def test_legacy_ib_ip_fallback(self):
        """ORCH_UT_NM_100: Template falls back to IB_IP for legacy CSVs."""
        assert "node.IB_IPV4 | default(node.IB_IP | default(''))" in self.template

    def test_ipv6_with_default_empty(self):
        """ORCH_UT_NM_101: Template handles missing IB_IPV6 with default('')."""
        assert "node.IB_IPV6 | default('')" in self.template

    def test_privacy_disabled_nmcli(self):
        """ORCH_UT_NM_102: Template disables privacy via nmcli."""
        assert "ipv6.ip6-privacy 0" in self.template

    def test_privacy_disabled_sysctl(self):
        """ORCH_UT_NM_103: Template disables privacy via sysctl (iproute2 path)."""
        assert "use_tempaddr=0" in self.template

    def test_ipv6_config_gated(self):
        """ORCH_UT_NM_104: IPv6 config is gated behind non-empty IB_IPV6."""
        # The template should only configure IPv6 when IB_IPV6 is non-empty
        assert 'if [ -n "$IB_IPV6" ]' in self.template

    def test_no_hardcoded_opt_omnia(self):
        """ORCH_UT_NM_105: Template uses no hardcoded /opt/omnia/ paths."""
        # Template may reference OMNIA_DATA_PATH env var but not hardcoded /opt/omnia
        lines = self.template.splitlines()
        for line in lines:
            if line.strip().startswith("#"):
                continue
            if line.strip().startswith("echo"):
                continue
            # Exclude env var default values
            if "OMNIA_DATA_PATH" in line:
                continue
            assert "/opt/omnia/" not in line or "default" in line, (
                f"Hardcoded /opt/omnia/ path found: {line.strip()}"
            )


# ===========================================================================
# TC-UT-005/006/007 extension: Cloud-init hosts injection, hosts distribution,
# IB interface discovery (ER-ORCH-005 post-implementation reconciliation)
# ===========================================================================

class TestCloudInitHostsRemoved:
    """Verify cloud-init /etc/hosts IPoIB injection was properly removed.

    NodeAddr in slurm.conf is sufficient for Slurm IB communication.
    Cloud-init /etc/hosts injection was removed in the review cleanup.
    """

    TEMPLATES_DIR = (
        _REPO_ROOT / "src" / "orchestrator" / "roles" / "provision_common"
        / "templates" / "metadata_svc"
    )

    def test_no_ib_hosts_entries_in_slurm_node_template(self):
        """ms-group-slurm_node_x86_64.yaml.j2 has no ib_hosts_entries (removed)."""
        template_path = self.TEMPLATES_DIR / "ms-group-slurm_node_x86_64.yaml.j2"
        if not template_path.exists():
            pytest.skip("Template not found (expected in orchestrator source)")
        content = template_path.read_text(encoding="utf-8")
        assert "ib_hosts_entries" not in content, (
            "ms-group-slurm_node_x86_64 still has ib_hosts_entries — should be removed"
        )

    def test_no_ib_hosts_entries_in_slurm_control_template(self):
        """ms-group-slurm_control_node_x86_64.yaml.j2 has no ib_hosts_entries."""
        template_path = self.TEMPLATES_DIR / "ms-group-slurm_control_node_x86_64.yaml.j2"
        if not template_path.exists():
            pytest.skip("Template not found")
        content = template_path.read_text(encoding="utf-8")
        assert "ib_hosts_entries" not in content

    def test_no_ib_hosts_entries_in_login_node_template(self):
        """ms-group-login_node_x86_64.yaml.j2 has no ib_hosts_entries."""
        template_path = self.TEMPLATES_DIR / "ms-group-login_node_x86_64.yaml.j2"
        if not template_path.exists():
            pytest.skip("Template not found")
        content = template_path.read_text(encoding="utf-8")
        assert "ib_hosts_entries" not in content

    def test_no_templates_have_ib_hosts_entries(self):
        """No ms-group-*.yaml.j2 templates reference ib_hosts_entries."""
        if not self.TEMPLATES_DIR.exists():
            pytest.skip("Templates directory not found")
        for tpl in self.TEMPLATES_DIR.glob("ms-group-*.yaml.j2"):
            content = tpl.read_text(encoding="utf-8")
            assert "ib_hosts_entries" not in content, (
                f"{tpl.name} still has ib_hosts_entries — should be removed"
            )


class TestHostsDistributionMergeLogic:
    """Verify the Python-based atomic merge logic used for compute node hosts distribution."""

    @staticmethod
    def _merge_hosts_block(existing_hosts: str, new_block: str) -> str:
        """Simulate the Python merge logic from publish_hosts.yml.

        This mirrors the inline Python3 script used in the 'Merge IPoIB hosts
        block into /etc/hosts on compute nodes' task.
        """
        marker_begin = "# BEGIN Omnia IPoIB managed block"
        marker_end = "# END Omnia IPoIB managed block"

        # Strip markers from new block
        lines = new_block.strip().split("\n")
        block = "\n".join(
            line for line in lines
            if not line.startswith("# BEGIN") and not line.startswith("# END")
        )

        if marker_begin in existing_hosts:
            result = re.sub(
                re.escape(marker_begin) + ".*?" + re.escape(marker_end),
                marker_begin + "\n" + block + "\n" + marker_end,
                existing_hosts,
                flags=re.DOTALL,
            )
        else:
            result = (
                existing_hosts.rstrip("\n") + "\n"
                + marker_begin + "\n" + block + "\n" + marker_end + "\n"
            )
        return result

    def test_first_insertion(self):
        """First insertion appends managed block with markers."""
        existing = "127.0.0.1 localhost\n"
        new_block = (
            "# BEGIN Omnia IPoIB managed block\n"
            "192.168.0.11 nid001-ib0\n"
            "# END Omnia IPoIB managed block\n"
        )
        result = self._merge_hosts_block(existing, new_block)
        assert "# BEGIN Omnia IPoIB managed block" in result
        assert "192.168.0.11 nid001-ib0" in result
        assert "# END Omnia IPoIB managed block" in result
        assert result.startswith("127.0.0.1 localhost")

    def test_replacement(self):
        """Existing managed block replaced atomically."""
        existing = (
            "127.0.0.1 localhost\n"
            "# BEGIN Omnia IPoIB managed block\n"
            "192.168.0.11 nid001-ib0\n"
            "# END Omnia IPoIB managed block\n"
        )
        new_block = (
            "# BEGIN Omnia IPoIB managed block\n"
            "192.168.0.11 nid001-ib0\n"
            "fd00:1b::11 nid001-ib0\n"
            "# END Omnia IPoIB managed block\n"
        )
        result = self._merge_hosts_block(existing, new_block)
        assert "fd00:1b::11 nid001-ib0" in result
        # Should have exactly one BEGIN marker
        assert result.count("# BEGIN Omnia IPoIB managed block") == 1

    def test_user_content_preserved(self):
        """Content outside markers preserved during replacement."""
        existing = (
            "127.0.0.1 localhost\n"
            "10.0.0.1 myserver\n"
            "# BEGIN Omnia IPoIB managed block\n"
            "old entry\n"
            "# END Omnia IPoIB managed block\n"
            "10.0.0.2 otherserver\n"
        )
        new_block = "# BEGIN Omnia IPoIB managed block\n192.168.0.11 nid001\n# END Omnia IPoIB managed block\n"
        result = self._merge_hosts_block(existing, new_block)
        assert "10.0.0.1 myserver" in result
        assert "10.0.0.2 otherserver" in result
        assert "old entry" not in result
        assert "192.168.0.11 nid001" in result
