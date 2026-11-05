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
"""Portable unit tests for diagnostics, failure states, and NFT security.

Story: ER-ORCH-005-diagnostics-failure-states
Supplements test_address_verifier.py (which requires Unix source_loader).

Covers:
- TC-UT-008: Address-State Verifier edge cases
- TC-NFT-004: No credentials in allocation exports or events
- TC-NFT-005: Privacy extension verification (security NFT)
- TC-NFT-006: Dual-stack degradation visibility (reliability NFT)
- Failure-mode decision matrix edge cases
- Structured event completeness

These tests import the address_verifier module directly via sys.path
without requiring fcntl or source_loader.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from unittest import mock

import pytest

# Set up module path to import address_verifier without source_loader/fcntl
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PLUGINS_DIR = _REPO_ROOT / "src" / "orchestrator" / "plugins"
sys.path.insert(0, str(_PLUGINS_DIR / "module_utils"))
sys.path.insert(0, str(_PLUGINS_DIR))

# Mock ansible.module_utils to allow import without ansible installed
sys.modules.setdefault("ansible", mock.MagicMock())
sys.modules.setdefault("ansible.module_utils", mock.MagicMock())
sys.modules.setdefault("ansible.module_utils.basic", mock.MagicMock())

from orchestrator_validation.renderers import (  # noqa: E402
    address_verifier as verifier,
)

pytestmark = pytest.mark.unit
LOGGER = logging.getLogger("diagnostics-ipv6-test")


# ---------------------------------------------------------------------------
# Simulated system outputs for edge case testing
# ---------------------------------------------------------------------------

_HEALTHY_DUAL_STACK = """\
2: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP
    inet6 fd00:1b::1/64 scope global manual preferred
       valid_lft forever preferred_lft forever
    inet6 fe80::1/64 scope link
       valid_lft forever preferred_lft forever
"""

_DEPRECATED_ADDR = """\
2: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044
    inet6 fd00:1b::1/64 scope global deprecated
       valid_lft forever preferred_lft 0sec
"""

_MULTIPLE_GLOBAL = """\
2: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044
    inet6 fd00:1b::1/64 scope global manual preferred
       valid_lft forever preferred_lft forever
    inet6 fd00:1b::abcd/64 scope global dynamic autoconf
       valid_lft 604800sec preferred_lft 86400sec
    inet6 fd00:1b::9999/64 scope global temporary mngtmpaddr
       valid_lft 604800sec preferred_lft 86400sec
    inet6 fd00:1b::dead/64 scope global
       valid_lft forever preferred_lft forever
    inet6 fe80::1/64 scope link
       valid_lft forever preferred_lft forever
"""

_EMPTY_OUTPUT = ""

_NO_ROUTES = """\
fd00:1b::/64 dev ib0 proto kernel metric 256 pref medium
fe80::/64 dev ib0 proto kernel metric 256 pref medium
"""

_DEFAULT_ROUTE_COLON = """\
::/0 via fd00:1b::ffff dev ib0 proto static metric 100
fd00:1b::/64 dev ib0 proto kernel metric 256 pref medium
"""

_PRIVACY_VALUE_1 = "net.ipv6.conf.ib0.use_tempaddr = 1"
_PRIVACY_UNPARSEABLE = "invalid output no equals sign"


# ===================================================================
# TC-UT-008 edge cases: Address-State Verifier
# ===================================================================

class TestAddressStateEdgeCases:
    """TC-UT-008 supplementary: edge cases for address verification."""

    def test_deprecated_address_flagged(self):
        """ORCH_UT_DIAG_001: Deprecated address is flagged as error."""
        result = verifier.verify_address_state(
            "fd00:1b::1", _DEPRECATED_ADDR, "nid0001", "ib0", LOGGER
        )
        assert result["found"] is True
        assert len(result["errors"]) >= 1
        assert any("deprecated" in e for e in result["errors"])

    def test_empty_ip_output_address_missing(self):
        """ORCH_UT_DIAG_002: Empty ip output reports address missing."""
        result = verifier.verify_address_state(
            "fd00:1b::1", _EMPTY_OUTPUT, "nid0001", "ib0", LOGGER
        )
        assert result["found"] is False
        assert result["dad_state"] == "missing"

    def test_compressed_vs_expanded_ipv6_match(self):
        """ORCH_UT_DIAG_003: Compressed and expanded IPv6 match correctly."""
        ip_output = """\
    inet6 fd00:001b:0000:0000:0000:0000:0000:0001/64 scope global manual preferred
"""
        result = verifier.verify_address_state(
            "fd00:1b::1", ip_output, "nid0001", "ib0"
        )
        assert result["found"] is True
        assert result["dad_state"] == "ok"


# ===================================================================
# TC-UT-008 edge cases: Autonomous address detection
# ===================================================================

class TestAutonomousAddressEdgeCases:
    """TC-UT-008 supplementary: autonomous address edge cases."""

    def test_multiple_autonomous_types_detected(self):
        """ORCH_UT_DIAG_010: Multiple autonomous types detected together."""
        result = verifier.detect_autonomous_addresses(
            _MULTIPLE_GLOBAL, ["fd00:1b::1"], "ib0", LOGGER
        )
        types = {r["type"] for r in result}
        # Should detect slaac, privacy, and unapproved_static
        assert len(result) >= 2
        assert "slaac" in types or "privacy" in types

    def test_empty_output_no_autonomous(self):
        """ORCH_UT_DIAG_011: Empty output yields no autonomous addresses."""
        result = verifier.detect_autonomous_addresses(
            _EMPTY_OUTPUT, ["fd00:1b::1"], "ib0"
        )
        assert result == []

    def test_all_approved_no_autonomous(self):
        """ORCH_UT_DIAG_012: When all addresses are approved, no autonomous."""
        ip_output = """\
    inet6 fd00:1b::1/64 scope global manual preferred
    inet6 fd00:1b::2/64 scope global manual preferred
    inet6 fe80::1/64 scope link
"""
        result = verifier.detect_autonomous_addresses(
            ip_output, ["fd00:1b::1", "fd00:1b::2"], "ib0"
        )
        assert result == []


# ===================================================================
# TC-UT-008 edge cases: Route verification
# ===================================================================

class TestRouteVerificationEdgeCases:
    """TC-UT-008 supplementary: route verification edge cases."""

    def test_colon_default_route_detected(self):
        """ORCH_UT_DIAG_020: ::/0 default route detected as error."""
        errors = verifier.verify_no_default_route(
            _DEFAULT_ROUTE_COLON, "ib0", LOGGER
        )
        assert len(errors) >= 1

    def test_empty_route_output_passes(self):
        """ORCH_UT_DIAG_021: Empty route output passes (no routes = no default)."""
        errors = verifier.verify_no_default_route(_EMPTY_OUTPUT, "ib0")
        assert errors == []


# ===================================================================
# TC-UT-008 edge cases: Privacy verification
# ===================================================================

class TestPrivacyVerificationEdgeCases:
    """TC-UT-008 supplementary: privacy verification edge cases."""

    def test_privacy_value_1_fails(self):
        """ORCH_UT_DIAG_030: use_tempaddr=1 fails (prefer public but allow temp)."""
        result = verifier.verify_privacy_disabled(
            _PRIVACY_VALUE_1, "ib0", LOGGER
        )
        assert result["disabled"] is False
        assert result["value"] == 1

    def test_unparseable_sysctl_fails(self):
        """ORCH_UT_DIAG_031: Unparseable sysctl output reports error."""
        result = verifier.verify_privacy_disabled(
            _PRIVACY_UNPARSEABLE, "ib0", LOGGER
        )
        assert result["disabled"] is False
        assert result["value"] is None
        assert result["error"] is not None


# ===================================================================
# TC-NFT-004: No credentials in events or exports (Security NFT)
# ===================================================================

class TestNoCredentialsInEvents:
    """TC-NFT-004: Events and exports never contain credential data."""

    def test_event_has_no_credential_keys(self):
        """ORCH_UT_DIAG_040: Event dict has no credential-related keys."""
        event = verifier.create_event(
            stage="address_state",
            result="HEALTHY",
            node_id="nid0001",
            interface_id="ib0",
            allocation_id="alloc-001",
            message="All checks passed",
        )
        forbidden_keys = {"password", "token", "secret", "key", "credential"}
        for key in event:
            assert key.lower() not in forbidden_keys, (
                f"Event contains forbidden key: {key}"
            )

    def test_event_values_no_credential_patterns(self):
        """ORCH_UT_DIAG_041: Event values don't contain credential patterns."""
        event = verifier.create_event(
            stage="test",
            result="FAILED",
            node_id="nid0001",
            interface_id="ib0",
            message="Address fd00:1b::1 not found on ib0",
        )
        credential_patterns = ["Bearer ", "ssh-rsa ", "BEGIN PRIVATE",
                               "vault_password", "ansible_ssh_pass"]
        for value in event.values():
            if isinstance(value, str):
                for pattern in credential_patterns:
                    assert pattern not in value, (
                        f"Event value contains credential pattern: {pattern}"
                    )

    def test_health_status_no_credential_leakage(self):
        """ORCH_UT_DIAG_042: Health result messages don't leak credentials."""
        health = verifier.determine_health_status(
            address_errors=["Address fd00:1b::1 not found on ib0"],
            autonomous_addrs=[],
            route_errors=[],
            peer_result=None,
            opensm_result=None,
            privacy_result=None,
            mode="dual-stack",
        )
        for value in [health["corrective_action"]] + health["errors"]:
            if isinstance(value, str):
                assert "password" not in value.lower()
                assert "token" not in value.lower()

    def test_event_correlation_id_generated(self):
        """ORCH_UT_DIAG_043: Each event gets a unique correlation ID."""
        e1 = verifier.create_event(stage="s1", result="OK", node_id="n1")
        e2 = verifier.create_event(stage="s2", result="OK", node_id="n1")
        assert e1["correlation_id"]
        assert e2["correlation_id"]
        assert e1["correlation_id"] != e2["correlation_id"]


# ===================================================================
# TC-NFT-005: Privacy extensions disabled (Security NFT)
# ===================================================================

class TestPrivacyExtensionsSecurity:
    """TC-NFT-005: Privacy extensions disabled on all covered interfaces."""

    def test_privacy_disabled_is_zero(self):
        """ORCH_UT_DIAG_050: use_tempaddr=0 is the only passing value."""
        for val in [0]:
            output = f"net.ipv6.conf.ib0.use_tempaddr = {val}"
            result = verifier.verify_privacy_disabled(output, "ib0")
            assert result["disabled"] is True

    def test_privacy_nonzero_values_fail(self):
        """ORCH_UT_DIAG_051: Any nonzero use_tempaddr fails verification."""
        for val in [1, 2, 3]:
            output = f"net.ipv6.conf.ib0.use_tempaddr = {val}"
            result = verifier.verify_privacy_disabled(output, "ib0")
            assert result["disabled"] is False, (
                f"use_tempaddr={val} should fail but was marked disabled"
            )

    def test_privacy_check_in_pipeline_causes_failure(self):
        """ORCH_UT_DIAG_052: Privacy enabled causes pipeline failure."""
        records = [{
            "address": "fd00:1b::1",
            "prefix_length": 64,
            "address_family": "ipv6",
        }]
        result = verifier.verify_interface(
            node_id="nid0001",
            interface_id="ib0",
            records=records,
            ip_addr_output=_HEALTHY_DUAL_STACK,
            ip_route_output=_NO_ROUTES,
            sysctl_output="net.ipv6.conf.ib0.use_tempaddr = 2",
            logger=LOGGER,
        )
        assert result["health"]["status"] != verifier.HealthStatus.HEALTHY
        assert result["privacy"]["disabled"] is False


# ===================================================================
# TC-NFT-006: Dual-stack degradation visible (Reliability NFT)
# ===================================================================

class TestDualStackDegradationVisibility:
    """TC-NFT-006: Dual-stack IPv6 failure is never silently ignored."""

    def test_dual_stack_failure_is_degraded_not_healthy(self):
        """ORCH_UT_DIAG_060: Dual-stack IPv6 failure is DEGRADED, not HEALTHY."""
        health = verifier.determine_health_status(
            address_errors=["Address not found"],
            autonomous_addrs=[],
            route_errors=[],
            peer_result=None,
            opensm_result=None,
            privacy_result=None,
            mode="dual-stack",
        )
        assert health["status"] == verifier.HealthStatus.DEGRADED_IPV6
        assert health["status"] != verifier.HealthStatus.HEALTHY

    def test_dual_stack_degraded_preserves_ipv4_note(self):
        """ORCH_UT_DIAG_061: DEGRADED_IPV6 notes IPv4 is operational."""
        health = verifier.determine_health_status(
            address_errors=["Address not found"],
            autonomous_addrs=[],
            route_errors=[],
            peer_result=None,
            opensm_result=None,
            privacy_result=None,
            mode="dual-stack",
        )
        assert "IPv4" in health["corrective_action"]

    def test_ipv6_only_failure_no_ipv4_fallback(self):
        """ORCH_UT_DIAG_062: IPv6-only failure has no IPv4 fallback note."""
        health = verifier.determine_health_status(
            address_errors=["Address not found"],
            autonomous_addrs=[],
            route_errors=[],
            peer_result=None,
            opensm_result=None,
            privacy_result=None,
            mode="ipv6-only",
        )
        assert health["status"] == verifier.HealthStatus.FAILED_IB_CONFIGURATION
        assert "No IPv4 fallback" in health["corrective_action"]

    def test_opensm_regression_trumps_degraded(self):
        """ORCH_UT_DIAG_063: OpenSM regression → RECOVERY even if address OK."""
        health = verifier.determine_health_status(
            address_errors=[],
            autonomous_addrs=[],
            route_errors=[],
            peer_result=None,
            opensm_result={"changed": True, "diffs": ["config"]},
            privacy_result=None,
            mode="dual-stack",
        )
        assert health["status"] == verifier.HealthStatus.RECOVERY_REQUIRED

    def test_multiple_failures_still_degraded(self):
        """ORCH_UT_DIAG_064: Multiple failures in dual-stack → DEGRADED_IPV6."""
        health = verifier.determine_health_status(
            address_errors=["missing"],
            autonomous_addrs=[{"address": "x", "type": "slaac"}],
            route_errors=["default route found"],
            peer_result={"reachable": False},
            opensm_result=None,
            privacy_result={"disabled": False, "error": "not disabled"},
            mode="dual-stack",
        )
        assert health["status"] == verifier.HealthStatus.DEGRADED_IPV6
        assert len(health["errors"]) >= 3


# ===================================================================
# Full pipeline edge cases
# ===================================================================

class TestFullPipelineEdgeCases:
    """Full verification pipeline edge cases."""

    def test_ipv4_only_records_skip_ipv6_checks(self):
        """ORCH_UT_DIAG_070: IPv4-only records don't trigger IPv6 checks."""
        records = [{
            "address": "10.0.100.1",
            "prefix_length": 24,
            "address_family": "ipv4",
        }]
        result = verifier.verify_interface(
            node_id="nid0001",
            interface_id="ib0",
            records=records,
            ip_addr_output=_EMPTY_OUTPUT,
            ip_route_output=_NO_ROUTES,
        )
        assert result["mode"] == "ipv4-only"
        # No IPv6 address checks should have been performed
        assert result["address_checks"] == []

    def test_dual_stack_mode_detection(self):
        """ORCH_UT_DIAG_071: Mixed IPv4+IPv6 records → dual-stack mode."""
        records = [
            {"address": "10.0.100.1", "prefix_length": 24, "address_family": "ipv4"},
            {"address": "fd00:1b::1", "prefix_length": 64, "address_family": "ipv6"},
        ]
        result = verifier.verify_interface(
            node_id="nid0001",
            interface_id="ib0",
            records=records,
            ip_addr_output=_HEALTHY_DUAL_STACK,
            ip_route_output=_NO_ROUTES,
        )
        assert result["mode"] == "dual-stack"

    def test_opensm_not_checked_when_no_snapshots(self):
        """ORCH_UT_DIAG_072: OpenSM check skipped when no snapshots provided."""
        records = [{
            "address": "fd00:1b::1",
            "prefix_length": 64,
            "address_family": "ipv6",
        }]
        result = verifier.verify_interface(
            node_id="nid0001",
            interface_id="ib0",
            records=records,
            ip_addr_output=_HEALTHY_DUAL_STACK,
            ip_route_output=_NO_ROUTES,
        )
        assert result["opensm"] is None

    def test_peer_not_checked_when_no_ping(self):
        """ORCH_UT_DIAG_073: Peer check skipped when no ping output."""
        records = [{
            "address": "fd00:1b::1",
            "prefix_length": 64,
            "address_family": "ipv6",
        }]
        result = verifier.verify_interface(
            node_id="nid0001",
            interface_id="ib0",
            records=records,
            ip_addr_output=_HEALTHY_DUAL_STACK,
            ip_route_output=_NO_ROUTES,
        )
        assert result["peer"] is None


# ===================================================================
# Structured event completeness
# ===================================================================

class TestStructuredEventCompleteness:
    """Structured [IB-IPv6] event completeness and identity fields."""

    def test_event_has_all_identity_fields(self):
        """ORCH_UT_DIAG_080: Event carries all required NFR-4 identity fields."""
        required_fields = {
            "prefix", "stage", "result", "cluster", "node",
            "fabric", "rail", "interface", "allocation_id",
            "correlation_id", "message",
        }
        event = verifier.create_event(
            stage="address_state",
            result="HEALTHY",
            node_id="nid0001",
            interface_id="ib0",
            allocation_id="alloc-001",
            fabric_id="fabric1",
            rail_id="rail1",
            cluster_id="cluster1",
            message="Passed",
        )
        assert required_fields.issubset(event.keys()), (
            f"Missing fields: {required_fields - event.keys()}"
        )

    def test_event_prefix_is_ib_ipv6(self):
        """ORCH_UT_DIAG_081: Event prefix is [IB-IPv6]."""
        event = verifier.create_event(
            stage="test", result="OK", node_id="n1"
        )
        assert event["prefix"] == "[IB-IPv6]"

    def test_health_status_enum_values(self):
        """ORCH_UT_DIAG_082: HealthStatus enum has all expected values."""
        expected = {"HEALTHY", "DEGRADED_IPV6",
                    "FAILED_IB_CONFIGURATION", "RECOVERY_REQUIRED"}
        actual = {s.value for s in verifier.HealthStatus}
        assert actual == expected

    def test_verification_stage_enum_values(self):
        """ORCH_UT_DIAG_083: VerificationStage enum has all expected values."""
        expected = {"address_state", "autonomous_address", "route_check",
                    "peer_reachability", "opensm_regression",
                    "privacy_check", "dad_check"}
        actual = {s.value for s in verifier.VerificationStage}
        assert actual == expected


# ===================================================================
# OpenSM snapshot computation
# ===================================================================

class TestOpenSMSnapshot:
    """OpenSM snapshot computation and comparison."""

    def test_snapshot_produces_checksums(self):
        """ORCH_UT_DIAG_090: Snapshot returns config/lid_gid/pkey checksums."""
        snap = verifier.compute_opensm_snapshot(
            "opensm.conf content", "lid/gid data", "pkey data"
        )
        assert "config" in snap
        assert "lid_gid" in snap
        assert "pkey" in snap
        assert len(snap["config"]) == 64  # SHA-256 hex

    def test_identical_inputs_identical_checksums(self):
        """ORCH_UT_DIAG_091: Same inputs produce same checksums."""
        s1 = verifier.compute_opensm_snapshot("a", "b", "c")
        s2 = verifier.compute_opensm_snapshot("a", "b", "c")
        assert s1 == s2

    def test_different_inputs_different_checksums(self):
        """ORCH_UT_DIAG_092: Different inputs produce different checksums."""
        s1 = verifier.compute_opensm_snapshot("a", "b", "c")
        s2 = verifier.compute_opensm_snapshot("a", "b", "d")
        assert s1 != s2

    def test_pkey_change_detected(self):
        """ORCH_UT_DIAG_093: P_Key change detected in comparison."""
        before = verifier.compute_opensm_snapshot("cfg", "lid", "pkey-v1")
        after = verifier.compute_opensm_snapshot("cfg", "lid", "pkey-v2")
        result = verifier.compare_opensm_snapshots(before, after)
        assert result["changed"] is True
        assert "pkey" in result["diffs"]
        assert "config" not in result["diffs"]
        assert "lid_gid" not in result["diffs"]
