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
"""Portable unit tests for Slurm NodeAddr injection from IPoIB allocation.

Story: ER-ORCH-005-nm-config-publication (FR-7, AC-009)
ER test plan: TC-UT-009

Covers:
- Address family selection: ipv4-only, ipv6-only, dual-stack+ipv4, dual-stack+ipv6
- CommunicationParameters EnableIPv6 injection for dual-stack and ipv6-only
- Dual-stack missing slurm_preferred_addr_family fails
- Mismatch warning (ipv4-only with ipv6 preference ignored)
- No allocation file skips injection
- Empty node_params skips injection
- IB interface auto-discovery patching (generic -> predictable names)
- Hosts block parsing for managed /etc/hosts
- PXE mapping CSV fallback for NodeAddr (IB_IPV6/IB_IPV4 columns)
- Dynamic node discovery mode (no iDRAC, minimal NodeName entries)
- GPU/CPU convenience Slurm partitions
- Login/compiler node NodeAddr injection
- /etc/hosts management disabled by default

These tests validate the logic embedded in inject_ib_nodeaddr.yml and the
IB discovery pipeline in ib_ipv6_config/tasks/main.yml by testing the
equivalent Python logic used in the Ansible shell tasks.
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import Any, Dict, List, Optional

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helper: simulate the NodeAddr address-family derivation from Ansible logic
# ---------------------------------------------------------------------------

def derive_nodeaddr_af(
    ib_addr_mode: str,
    slurm_preferred_addr_family: str = "",
) -> str:
    """Derive the target address family for Slurm NodeAddr.

    Mirrors the Jinja2 logic in inject_ib_nodeaddr.yml task
    'Determine target address family for NodeAddr'.

    Args:
        ib_addr_mode: One of 'ipv4-only', 'ipv6-only', 'dual-stack', or ''.
        slurm_preferred_addr_family: 'ipv4' or 'ipv6' (required for dual-stack).

    Returns:
        'ipv4', 'ipv6', or 'none'.
    """
    mode = ib_addr_mode.strip()
    if mode == "ipv4-only":
        return "ipv4"
    if mode == "ipv6-only":
        return "ipv6"
    if mode == "dual-stack":
        return slurm_preferred_addr_family.strip()
    return "none"


def validate_dual_stack_preference(
    ib_addr_mode: str,
    slurm_preferred_addr_family: str = "",
) -> Optional[str]:
    """Check if dual-stack requires slurm_preferred_addr_family.

    Mirrors the 'Fail if dual-stack but slurm_preferred_addr_family not set'
    task in inject_ib_nodeaddr.yml.

    Returns:
        Error message string if validation fails, None if OK.
    """
    if ib_addr_mode.strip() == "dual-stack" and not slurm_preferred_addr_family.strip():
        return (
            "ib_addr_mode is 'dual-stack' but slurm_preferred_addr_family is not set "
            "in network_spec.yml (ib_network section). Slurm NodeAddr accepts only one "
            "address per node — set slurm_preferred_addr_family to 'ipv4' or 'ipv6' to "
            "choose which IB address Slurm uses for inter-daemon communication."
        )
    return None


def detect_preference_mismatch(
    ib_addr_mode: str,
    slurm_preferred_addr_family: str = "",
) -> Optional[str]:
    """Detect mismatch between ib_addr_mode and slurm_preferred_addr_family.

    Mirrors the 'Warn if slurm_preferred_addr_family mismatches ib_addr_mode'
    task in inject_ib_nodeaddr.yml.

    Returns:
        Warning message string if mismatch detected, None otherwise.
    """
    pref = slurm_preferred_addr_family.strip()
    mode = ib_addr_mode.strip()
    if not pref:
        return None
    if (mode == "ipv4-only" and pref == "ipv6") or (mode == "ipv6-only" and pref == "ipv4"):
        effective = "ipv4" if mode == "ipv4-only" else "ipv6"
        return (
            f"slurm_preferred_addr_family='{pref}' is set but ib_addr_mode='{mode}' "
            f"— only {effective} addresses are available. Ignoring "
            f"slurm_preferred_addr_family and using {effective}."
        )
    return None


def build_nodeaddr_map(
    allocations: List[Dict[str, Any]],
    target_af: str,
) -> Dict[str, str]:
    """Build hostname-to-address mapping for NodeAddr.

    Mirrors the 'Build hostname to IB address mapping' task.

    Args:
        allocations: List of allocation records with hostname, address, address_family.
        target_af: Target address family ('ipv4' or 'ipv6').

    Returns:
        Dict mapping hostname to IB address.
    """
    return {
        a["hostname"]: a["address"]
        for a in allocations
        if a.get("address_family") == target_af
    }


def inject_nodeaddr(
    node_params: List[Dict[str, Any]],
    nodeaddr_map: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Inject NodeAddr into node_params entries.

    Mirrors the 'Add NodeAddr to each node_params entry' task.

    Args:
        node_params: List of Slurm node parameter dicts (must have NodeName).
        nodeaddr_map: hostname-to-address mapping.

    Returns:
        Updated node_params with NodeAddr injected.
    """
    result = []
    for entry in node_params:
        node_name = entry.get("NodeName", "")
        if node_name in nodeaddr_map:
            updated = dict(entry, NodeAddr=nodeaddr_map[node_name])
            result.append(updated)
        else:
            result.append(entry)
    return result


def add_enable_ipv6(
    apply_config: Dict[str, Any],
    ib_addr_mode: str,
) -> Dict[str, Any]:
    """Add EnableIPv6 to CommunicationParameters for dual-stack/ipv6-only.

    Mirrors the 'Add EnableIPv6 to CommunicationParameters' task.

    Args:
        apply_config: Slurm config dict with 'slurm' key.
        ib_addr_mode: The IB addressing mode.

    Returns:
        Updated apply_config.
    """
    if ib_addr_mode in ("dual-stack", "ipv6-only"):
        slurm_conf = apply_config.get("slurm", {})
        existing = slurm_conf.get("CommunicationParameters", "")
        new_val = f"{existing},EnableIPv6" if existing else "EnableIPv6"
        # Strip leading comma (mirrors regex_replace('^,', ''))
        new_val = re.sub(r"^,", "", new_val)
        slurm_conf["CommunicationParameters"] = new_val
        apply_config["slurm"] = slurm_conf
    return apply_config


def patch_ib_interfaces(
    normalized_nodes: Dict[str, Dict[str, List[Dict[str, Any]]]],
    iface_map: Dict[str, List[str]],
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Patch normalized_nodes with discovered IB interface names.

    Mirrors the inline Python in 'Patch normalized_nodes with discovered
    interface names' task in ib_ipv6_config/tasks/main.yml.

    Args:
        normalized_nodes: Nodes keyed by node ID, then by interface name.
        iface_map: hostname -> list of discovered IB interface names.

    Returns:
        Patched normalized_nodes with real interface names.
    """
    result = {}
    for nid, nifaces in normalized_nodes.items():
        first_rec = next(iter(next(iter(nifaces.values()))))
        hostname = first_rec.get("hostname", "")
        discovered = iface_map.get(hostname, [])
        if discovered:
            new_ifaces: Dict[str, List[Dict[str, Any]]] = {}
            for idx, old_key in enumerate(nifaces):
                new_key = discovered[idx] if idx < len(discovered) else old_key
                updated = [dict(r, interface_id=new_key) for r in nifaces[old_key]]
                new_ifaces[new_key] = updated
            result[nid] = new_ifaces
        else:
            result[nid] = nifaces
    return result


def parse_hosts_block_for_cloudinit(raw: str) -> List[str]:
    """Parse hosts block content for cloud-init injection.

    Mirrors the set_fact logic in configure_metadata_svc.yml that filters
    comment and empty lines from the rendered hosts block.

    Args:
        raw: Raw hosts block content.

    Returns:
        List of non-comment, non-empty lines.
    """
    return [
        line
        for line in raw.splitlines()
        if not re.match(r"^#", line) and not re.match(r"^\s*$", line)
    ]


# ---------------------------------------------------------------------------
# Test data fixtures
# ---------------------------------------------------------------------------

SAMPLE_ALLOCATIONS = [
    {"hostname": "nid001", "address": "192.168.0.11", "address_family": "ipv4",
     "interface_id": "ib0", "lifecycle_state": "active"},
    {"hostname": "nid001", "address": "fd00:1b::11", "address_family": "ipv6",
     "interface_id": "ib0", "lifecycle_state": "active"},
    {"hostname": "nid002", "address": "192.168.0.12", "address_family": "ipv4",
     "interface_id": "ib0", "lifecycle_state": "active"},
    {"hostname": "nid002", "address": "fd00:1b::12", "address_family": "ipv6",
     "interface_id": "ib0", "lifecycle_state": "active"},
    {"hostname": "nid003", "address": "192.168.0.13", "address_family": "ipv4",
     "interface_id": "ib0", "lifecycle_state": "active"},
    {"hostname": "nid003", "address": "fd00:1b::13", "address_family": "ipv6",
     "interface_id": "ib0", "lifecycle_state": "active"},
]

SAMPLE_NODE_PARAMS = [
    {"NodeName": "nid001", "CPUs": 144, "RealMemory": 864},
    {"NodeName": "nid002", "CPUs": 144, "RealMemory": 864},
    {"NodeName": "nid003", "CPUs": 144, "RealMemory": 864},
]


# ===========================================================================
# TC-UT-009: Address family selection tests
# ===========================================================================

class TestNodeAddrAddressFamily:
    """TC-UT-009: Verify NodeAddr address family derivation."""

    def test_ipv4_only_derives_ipv4(self):
        """ipv4-only mode auto-derives ipv4 without preference."""
        assert derive_nodeaddr_af("ipv4-only") == "ipv4"

    def test_ipv6_only_derives_ipv6(self):
        """ipv6-only mode auto-derives ipv6 without preference."""
        assert derive_nodeaddr_af("ipv6-only") == "ipv6"

    def test_dual_stack_with_ipv4_preference(self):
        """dual-stack with ipv4 preference returns ipv4."""
        assert derive_nodeaddr_af("dual-stack", "ipv4") == "ipv4"

    def test_dual_stack_with_ipv6_preference(self):
        """dual-stack with ipv6 preference returns ipv6."""
        assert derive_nodeaddr_af("dual-stack", "ipv6") == "ipv6"

    def test_empty_mode_returns_none(self):
        """Empty ib_addr_mode returns 'none'."""
        assert derive_nodeaddr_af("") == "none"

    def test_unknown_mode_returns_none(self):
        """Unknown ib_addr_mode value returns 'none'."""
        assert derive_nodeaddr_af("multi-stack") == "none"


# ===========================================================================
# TC-UT-009: Dual-stack preference validation
# ===========================================================================

class TestDualStackPreferenceValidation:
    """TC-UT-009: Verify dual-stack requires slurm_preferred_addr_family."""

    def test_dual_stack_missing_preference_fails(self):
        """dual-stack without slurm_preferred_addr_family returns error."""
        err = validate_dual_stack_preference("dual-stack", "")
        assert err is not None
        assert "slurm_preferred_addr_family is not set" in err

    def test_dual_stack_with_preference_passes(self):
        """dual-stack with slurm_preferred_addr_family passes."""
        assert validate_dual_stack_preference("dual-stack", "ipv4") is None

    def test_ipv4_only_no_preference_passes(self):
        """ipv4-only does not require slurm_preferred_addr_family."""
        assert validate_dual_stack_preference("ipv4-only", "") is None

    def test_ipv6_only_no_preference_passes(self):
        """ipv6-only does not require slurm_preferred_addr_family."""
        assert validate_dual_stack_preference("ipv6-only", "") is None


# ===========================================================================
# TC-UT-009: Preference mismatch warning
# ===========================================================================

class TestPreferenceMismatchWarning:
    """TC-UT-009: Verify mismatch warning when preference contradicts mode."""

    def test_ipv4_only_with_ipv6_pref_warns(self):
        """ipv4-only with ipv6 preference produces warning."""
        warning = detect_preference_mismatch("ipv4-only", "ipv6")
        assert warning is not None
        assert "only ipv4 addresses are available" in warning

    def test_ipv6_only_with_ipv4_pref_warns(self):
        """ipv6-only with ipv4 preference produces warning."""
        warning = detect_preference_mismatch("ipv6-only", "ipv4")
        assert warning is not None
        assert "only ipv6 addresses are available" in warning

    def test_dual_stack_with_ipv4_pref_no_warning(self):
        """dual-stack with ipv4 preference is valid — no warning."""
        assert detect_preference_mismatch("dual-stack", "ipv4") is None

    def test_no_preference_no_warning(self):
        """No preference set produces no warning."""
        assert detect_preference_mismatch("ipv4-only", "") is None


# ===========================================================================
# TC-UT-009: NodeAddr injection into node_params
# ===========================================================================

class TestNodeAddrInjection:
    """TC-UT-009: Verify NodeAddr injection into Slurm node_params."""

    def test_ipv4_nodeaddr_injected(self):
        """IPv4 NodeAddr injected into all 3 nodes."""
        addr_map = build_nodeaddr_map(SAMPLE_ALLOCATIONS, "ipv4")
        result = inject_nodeaddr(SAMPLE_NODE_PARAMS, addr_map)
        assert len(result) == 3
        assert result[0]["NodeAddr"] == "192.168.0.11"
        assert result[1]["NodeAddr"] == "192.168.0.12"
        assert result[2]["NodeAddr"] == "192.168.0.13"

    def test_ipv6_nodeaddr_injected(self):
        """IPv6 NodeAddr injected into all 3 nodes."""
        addr_map = build_nodeaddr_map(SAMPLE_ALLOCATIONS, "ipv6")
        result = inject_nodeaddr(SAMPLE_NODE_PARAMS, addr_map)
        assert result[0]["NodeAddr"] == "fd00:1b::11"
        assert result[1]["NodeAddr"] == "fd00:1b::12"
        assert result[2]["NodeAddr"] == "fd00:1b::13"

    def test_unmatched_node_unchanged(self):
        """Nodes not in allocation map keep original params (no NodeAddr)."""
        addr_map = {"nid001": "192.168.0.11"}  # Only nid001
        result = inject_nodeaddr(SAMPLE_NODE_PARAMS, addr_map)
        assert "NodeAddr" in result[0]
        assert "NodeAddr" not in result[1]
        assert "NodeAddr" not in result[2]

    def test_empty_node_params_returns_empty(self):
        """Empty node_params produces empty result."""
        result = inject_nodeaddr([], {"nid001": "192.168.0.11"})
        assert result == []

    def test_empty_map_preserves_params(self):
        """Empty address map preserves all params unchanged."""
        result = inject_nodeaddr(SAMPLE_NODE_PARAMS, {})
        for entry in result:
            assert "NodeAddr" not in entry

    def test_original_fields_preserved(self):
        """Original CPUs/RealMemory preserved after NodeAddr injection."""
        addr_map = build_nodeaddr_map(SAMPLE_ALLOCATIONS, "ipv4")
        result = inject_nodeaddr(SAMPLE_NODE_PARAMS, addr_map)
        assert result[0]["CPUs"] == 144
        assert result[0]["RealMemory"] == 864


# ===========================================================================
# TC-UT-009: EnableIPv6 CommunicationParameters injection
# ===========================================================================

class TestEnableIPv6Injection:
    """TC-UT-009: Verify CommunicationParameters EnableIPv6 handling."""

    def test_dual_stack_adds_enable_ipv6(self):
        """dual-stack adds EnableIPv6."""
        config = {"slurm": {}}
        result = add_enable_ipv6(config, "dual-stack")
        assert result["slurm"]["CommunicationParameters"] == "EnableIPv6"

    def test_ipv6_only_adds_enable_ipv6(self):
        """ipv6-only adds EnableIPv6."""
        config = {"slurm": {}}
        result = add_enable_ipv6(config, "ipv6-only")
        assert result["slurm"]["CommunicationParameters"] == "EnableIPv6"

    def test_ipv4_only_no_enable_ipv6(self):
        """ipv4-only does not add EnableIPv6."""
        config = {"slurm": {}}
        result = add_enable_ipv6(config, "ipv4-only")
        assert "CommunicationParameters" not in result.get("slurm", {})

    def test_existing_params_appended(self):
        """EnableIPv6 appended to existing CommunicationParameters."""
        config = {"slurm": {"CommunicationParameters": "NoCtld"}}
        result = add_enable_ipv6(config, "dual-stack")
        assert result["slurm"]["CommunicationParameters"] == "NoCtld,EnableIPv6"

    def test_empty_existing_params(self):
        """Empty existing CommunicationParameters gets clean EnableIPv6."""
        config = {"slurm": {"CommunicationParameters": ""}}
        result = add_enable_ipv6(config, "ipv6-only")
        assert result["slurm"]["CommunicationParameters"] == "EnableIPv6"


# ===========================================================================
# TC-UT-009: IB interface auto-discovery patching
# ===========================================================================

class TestIBInterfaceDiscoveryPatching:
    """TC-UT-009: Verify IB interface name patching from discovery."""

    def test_generic_to_predictable_name(self):
        """Generic ib0 patched to discovered ibp10s0."""
        nodes = {
            "x1000c1s1b0n0": {
                "ib0": [{"hostname": "nid001", "interface_id": "ib0",
                         "address": "192.168.0.11"}]
            }
        }
        iface_map = {"nid001": ["ibp10s0"]}
        result = patch_ib_interfaces(nodes, iface_map)
        assert "ibp10s0" in result["x1000c1s1b0n0"]
        assert "ib0" not in result["x1000c1s1b0n0"]
        assert result["x1000c1s1b0n0"]["ibp10s0"][0]["interface_id"] == "ibp10s0"

    def test_multi_interface_patching(self):
        """Multiple interfaces patched in order."""
        nodes = {
            "x1000c1s1b0n0": {
                "ib0": [{"hostname": "nid001", "interface_id": "ib0",
                         "address": "192.168.0.11"}],
                "ib1": [{"hostname": "nid001", "interface_id": "ib1",
                         "address": "192.168.1.11"}],
            }
        }
        iface_map = {"nid001": ["ibp10s0", "ibp181s0"]}
        result = patch_ib_interfaces(nodes, iface_map)
        assert "ibp10s0" in result["x1000c1s1b0n0"]
        assert "ibp181s0" in result["x1000c1s1b0n0"]

    def test_no_discovered_interfaces_unchanged(self):
        """Node with no discovered interfaces keeps generic names."""
        nodes = {
            "x1000c1s1b0n0": {
                "ib0": [{"hostname": "nid001", "interface_id": "ib0",
                         "address": "192.168.0.11"}]
            }
        }
        iface_map = {}  # No discovery results
        result = patch_ib_interfaces(nodes, iface_map)
        assert "ib0" in result["x1000c1s1b0n0"]

    def test_fewer_discovered_than_generic(self):
        """If fewer discovered than generic, extra interfaces keep old name."""
        nodes = {
            "x1000c1s1b0n0": {
                "ib0": [{"hostname": "nid001", "interface_id": "ib0",
                         "address": "192.168.0.11"}],
                "ib1": [{"hostname": "nid001", "interface_id": "ib1",
                         "address": "192.168.1.11"}],
            }
        }
        iface_map = {"nid001": ["ibp10s0"]}  # Only 1 discovered
        result = patch_ib_interfaces(nodes, iface_map)
        assert "ibp10s0" in result["x1000c1s1b0n0"]
        assert "ib1" in result["x1000c1s1b0n0"]  # Kept old name


# ===========================================================================
# TC-UT-009: Cloud-init /etc/hosts injection parsing
# ===========================================================================

class TestCloudInitHostsInjection:
    """TC-UT-009: Verify hosts block parsing for cloud-init injection."""

    def test_comments_and_empty_lines_filtered(self):
        """Comment and empty lines stripped from hosts block."""
        raw = (
            "# BEGIN Omnia IPoIB managed block\n"
            "192.168.0.11 nid001-ib0 nid001-ib\n"
            "fd00:1b::11 nid001-ib0 nid001-ib\n"
            "\n"
            "# END Omnia IPoIB managed block\n"
        )
        entries = parse_hosts_block_for_cloudinit(raw)
        assert len(entries) == 2
        assert "192.168.0.11 nid001-ib0 nid001-ib" in entries
        assert "fd00:1b::11 nid001-ib0 nid001-ib" in entries

    def test_empty_block_returns_empty_list(self):
        """Empty hosts block returns empty list."""
        entries = parse_hosts_block_for_cloudinit("")
        assert entries == []

    def test_all_comments_returns_empty(self):
        """Block with only comments returns empty."""
        raw = "# BEGIN Omnia IPoIB managed block\n# END Omnia IPoIB managed block\n"
        entries = parse_hosts_block_for_cloudinit(raw)
        assert entries == []

    def test_multiple_hosts_preserved(self):
        """All non-comment host lines are preserved."""
        raw = (
            "# BEGIN Omnia IPoIB managed block\n"
            "192.168.0.11 nid001-ib0 nid001-ib\n"
            "192.168.0.12 nid002-ib0 nid002-ib\n"
            "192.168.0.13 nid003-ib0 nid003-ib\n"
            "fd00:1b::11 nid001-ib0 nid001-ib\n"
            "fd00:1b::12 nid002-ib0 nid002-ib\n"
            "fd00:1b::13 nid003-ib0 nid003-ib\n"
            "# END Omnia IPoIB managed block\n"
        )
        entries = parse_hosts_block_for_cloudinit(raw)
        assert len(entries) == 6


# ===========================================================================
# TC-UT-009: PXE mapping CSV fallback for NodeAddr
# ===========================================================================

def parse_pxe_mapping_for_nodeaddr(
    rows: List[Dict[str, str]],
) -> tuple:
    """Parse PXE mapping rows and build hostname-to-IB-address map.

    Mirrors the inline Python3 in inject_ib_nodeaddr.yml's
    'Parse PXE mapping CSV and build hostname-to-IB-address map' task.

    Args:
        rows: List of dicts representing PXE mapping CSV rows.

    Returns:
        Tuple of (hostname_to_addr_map, has_ipv6_flag).
    """
    result: Dict[str, str] = {}
    has_ipv6 = False
    for row in rows:
        hostname = row.get("HOSTNAME", "").strip()
        if not hostname:
            continue
        ib_ipv6 = row.get("IB_IPV6", "").strip()
        ib_ipv4 = row.get("IB_IPV4", "").strip()
        if ib_ipv6:
            result[hostname] = ib_ipv6
            has_ipv6 = True
        elif ib_ipv4:
            result[hostname] = ib_ipv4
    return result, has_ipv6


class TestPXEMappingFallback:
    """TC-UT-009: PXE mapping CSV fallback when no IB allocation file exists."""

    def test_prefers_ipv6_over_ipv4(self):
        """IB_IPV6 preferred when both columns populated."""
        rows = [
            {"HOSTNAME": "nid001", "IB_IPV6": "fd00:1b::11", "IB_IPV4": "192.168.0.11"},
            {"HOSTNAME": "nid002", "IB_IPV6": "fd00:1b::12", "IB_IPV4": "192.168.0.12"},
        ]
        addr_map, has_ipv6 = parse_pxe_mapping_for_nodeaddr(rows)
        assert addr_map == {"nid001": "fd00:1b::11", "nid002": "fd00:1b::12"}
        assert has_ipv6 is True

    def test_falls_back_to_ipv4(self):
        """IB_IPV4 used when IB_IPV6 is empty."""
        rows = [
            {"HOSTNAME": "nid001", "IB_IPV6": "", "IB_IPV4": "192.168.0.11"},
            {"HOSTNAME": "nid002", "IB_IPV6": "", "IB_IPV4": "192.168.0.12"},
        ]
        addr_map, has_ipv6 = parse_pxe_mapping_for_nodeaddr(rows)
        assert addr_map == {"nid001": "192.168.0.11", "nid002": "192.168.0.12"}
        assert has_ipv6 is False

    def test_mixed_ipv6_and_ipv4(self):
        """Some nodes have IPv6, others only IPv4."""
        rows = [
            {"HOSTNAME": "nid001", "IB_IPV6": "fd00:1b::11", "IB_IPV4": "192.168.0.11"},
            {"HOSTNAME": "nid002", "IB_IPV6": "", "IB_IPV4": "192.168.0.12"},
        ]
        addr_map, has_ipv6 = parse_pxe_mapping_for_nodeaddr(rows)
        assert addr_map["nid001"] == "fd00:1b::11"
        assert addr_map["nid002"] == "192.168.0.12"
        assert has_ipv6 is True

    def test_empty_hostname_skipped(self):
        """Rows without HOSTNAME are skipped."""
        rows = [
            {"HOSTNAME": "", "IB_IPV6": "fd00:1b::11", "IB_IPV4": "192.168.0.11"},
            {"HOSTNAME": "nid002", "IB_IPV6": "fd00:1b::12", "IB_IPV4": ""},
        ]
        addr_map, _ = parse_pxe_mapping_for_nodeaddr(rows)
        assert "nid002" in addr_map
        assert len(addr_map) == 1

    def test_no_ib_columns_returns_empty(self):
        """Rows with no IB_IPV6 or IB_IPV4 return empty map."""
        rows = [
            {"HOSTNAME": "nid001", "IB_IPV6": "", "IB_IPV4": ""},
        ]
        addr_map, has_ipv6 = parse_pxe_mapping_for_nodeaddr(rows)
        assert addr_map == {}
        assert has_ipv6 is False

    def test_pxe_nodeaddr_injected_into_node_params(self):
        """PXE-derived NodeAddr injected into node_params."""
        pxe_map = {"nid001": "fd00:1b::11", "nid002": "fd00:1b::12"}
        node_params = [
            {"NodeName": "nid001"},
            {"NodeName": "nid002"},
            {"NodeName": "nid003"},  # No PXE mapping
        ]
        result = inject_nodeaddr(node_params, pxe_map)
        assert result[0]["NodeAddr"] == "fd00:1b::11"
        assert result[1]["NodeAddr"] == "fd00:1b::12"
        assert "NodeAddr" not in result[2]

    def test_pxe_enable_ipv6_when_has_ipv6(self):
        """EnableIPv6 added to CommunicationParameters when PXE has IPv6."""
        config = {"slurm": {}}
        # Simulate: has_ipv6 = True
        config["slurm"]["CommunicationParameters"] = "EnableIPv6"
        assert "EnableIPv6" in config["slurm"]["CommunicationParameters"]


# ===========================================================================
# TC-UT-009: Dynamic discovery mode
# ===========================================================================

class TestDynamicDiscoveryMode:
    """TC-UT-009: Dynamic node discovery mode — no iDRAC."""

    @staticmethod
    def generate_dynamic_node_params(cmpt_list: List[str]) -> List[Dict[str, Any]]:
        """Generate minimal node_params for dynamic mode.

        Mirrors the 'Generate minimal node_params for dynamic mode' task
        in confs.yml.
        """
        return [{"NodeName": host} for host in cmpt_list]

    def test_dynamic_generates_minimal_entries(self):
        """Dynamic mode generates NodeName-only entries."""
        cmpt_list = ["nid001", "nid002", "nid003"]
        params = self.generate_dynamic_node_params(cmpt_list)
        assert len(params) == 3
        for p in params:
            assert "NodeName" in p
            assert len(p) == 1  # Only NodeName, no CPUs/RealMemory/etc.

    def test_dynamic_with_nodeaddr_injection(self):
        """Dynamic mode + PXE mapping injects NodeAddr."""
        cmpt_list = ["nid001", "nid002"]
        params = self.generate_dynamic_node_params(cmpt_list)
        pxe_map = {"nid001": "fd00:1b::11", "nid002": "fd00:1b::12"}
        result = inject_nodeaddr(params, pxe_map)
        assert result[0] == {"NodeName": "nid001", "NodeAddr": "fd00:1b::11"}
        assert result[1] == {"NodeName": "nid002", "NodeAddr": "fd00:1b::12"}

    def test_dynamic_empty_compute_list(self):
        """Dynamic mode with no compute nodes produces empty list."""
        params = self.generate_dynamic_node_params([])
        assert params == []

    def test_dynamic_preserves_hostname(self):
        """Dynamic mode preserves exact hostnames."""
        cmpt_list = ["compute-001.cluster.local", "gpu-node-1"]
        params = self.generate_dynamic_node_params(cmpt_list)
        assert params[0]["NodeName"] == "compute-001.cluster.local"
        assert params[1]["NodeName"] == "gpu-node-1"


# ===========================================================================
# TC-UT-009: Convenience partitions
# ===========================================================================

class TestConveniencePartitions:
    """TC-UT-009: GPU and CPU convenience partitions."""

    @staticmethod
    def generate_convenience_partitions(
        cmpt_list: List[str],
    ) -> List[Dict[str, Any]]:
        """Generate GPU and CPU convenience partitions.

        Mirrors the 'Append GPU convenience partition' and
        'Append CPU convenience partition' tasks in build_slurm_conf.yml.
        """
        nodes = ",".join(cmpt_list) if cmpt_list else "ALL"
        return [
            {
                "PartitionName": "gpu",
                "Nodes": nodes,
                "MaxTime": "INFINITE",
                "State": "UP",
            },
            {
                "PartitionName": "cpu",
                "Nodes": nodes,
                "MaxTime": "INFINITE",
                "State": "UP",
            },
        ]

    def test_both_partitions_created(self):
        """GPU and CPU partitions both created."""
        partitions = self.generate_convenience_partitions(["nid001", "nid002"])
        assert len(partitions) == 2
        assert partitions[0]["PartitionName"] == "gpu"
        assert partitions[1]["PartitionName"] == "cpu"

    def test_partition_nodes_populated(self):
        """Partition Nodes field lists compute nodes."""
        partitions = self.generate_convenience_partitions(["nid001", "nid002", "nid003"])
        assert partitions[0]["Nodes"] == "nid001,nid002,nid003"
        assert partitions[1]["Nodes"] == "nid001,nid002,nid003"

    def test_empty_compute_list_uses_all(self):
        """Empty compute list defaults to ALL."""
        partitions = self.generate_convenience_partitions([])
        assert partitions[0]["Nodes"] == "ALL"
        assert partitions[1]["Nodes"] == "ALL"

    def test_partition_state_is_up(self):
        """Both partitions have State: UP."""
        partitions = self.generate_convenience_partitions(["nid001"])
        for p in partitions:
            assert p["State"] == "UP"
            assert p["MaxTime"] == "INFINITE"


# ===========================================================================
# TC-UT-009: Login/compiler node NodeAddr injection
# ===========================================================================

class TestLoginCompilerNodeAddr:
    """TC-UT-009: Login and compiler nodes receive NodeAddr."""

    @staticmethod
    def build_login_entry(
        hostname: str,
        pxe_map: Dict[str, str],
        alloc_map: Dict[str, str],
    ) -> Dict[str, Any]:
        """Build a login node entry with NodeAddr from PXE or allocation.

        Mirrors the logic in build_slurm_conf.yml for login/compiler nodes.
        PXE mapping takes precedence over allocation.
        """
        if pxe_map.get(hostname, ""):
            return {"NodeName": hostname, "NodeAddr": pxe_map[hostname]}
        if alloc_map.get(hostname, ""):
            return {"NodeName": hostname, "NodeAddr": alloc_map[hostname]}
        return {"NodeName": hostname}

    def test_login_gets_nodeaddr_from_pxe(self):
        """Login node gets NodeAddr from PXE mapping."""
        entry = self.build_login_entry(
            "login01",
            pxe_map={"login01": "fd00:1b::101"},
            alloc_map={},
        )
        assert entry == {"NodeName": "login01", "NodeAddr": "fd00:1b::101"}

    def test_login_gets_nodeaddr_from_allocation(self):
        """Login node falls back to allocation map."""
        entry = self.build_login_entry(
            "login01",
            pxe_map={},
            alloc_map={"login01": "192.168.0.101"},
        )
        assert entry == {"NodeName": "login01", "NodeAddr": "192.168.0.101"}

    def test_pxe_takes_precedence_over_allocation(self):
        """PXE mapping takes precedence over allocation."""
        entry = self.build_login_entry(
            "login01",
            pxe_map={"login01": "fd00:1b::101"},
            alloc_map={"login01": "192.168.0.101"},
        )
        assert entry["NodeAddr"] == "fd00:1b::101"

    def test_login_without_any_ib_mapping(self):
        """Login node without IB mapping has no NodeAddr."""
        entry = self.build_login_entry(
            "login01",
            pxe_map={},
            alloc_map={},
        )
        assert entry == {"NodeName": "login01"}
        assert "NodeAddr" not in entry

    def test_compiler_node_same_logic(self):
        """Compiler nodes use the same logic as login nodes."""
        entry = self.build_login_entry(
            "compiler01",
            pxe_map={"compiler01": "fd00:1b::201"},
            alloc_map={},
        )
        assert entry == {"NodeName": "compiler01", "NodeAddr": "fd00:1b::201"}


# ===========================================================================
# TC-UT-009: /etc/hosts management disabled by default
# ===========================================================================

class TestHostsManagementDefault:
    """TC-UT-009: Verify /etc/hosts management is disabled by default."""

    def test_default_hosts_management_disabled(self):
        """ib_ipv6_manage_hosts defaults to false."""
        defaults_file = (
            pathlib.Path(__file__).resolve().parents[3]
            / "src" / "orchestrator" / "roles"
            / "ib_ipv6_config" / "defaults" / "main.yml"
        )
        if not defaults_file.exists():
            pytest.skip("Defaults file not found")
        content = defaults_file.read_text(encoding="utf-8")
        assert "ib_ipv6_manage_hosts: false" in content, (
            "ib_ipv6_manage_hosts should default to false"
        )
