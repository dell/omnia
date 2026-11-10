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
"""Unit tests for address verifier, diagnostics, and failure states (ER-ORCH-005).

Covers TC-UT-008 (Verification Layer), TC-FVT-014 to TC-FVT-017,
and TC-NFT-004 to TC-NFT-006 from the ER test plan.
"""

from __future__ import annotations

import logging

import pytest

from ut import source_loader  # noqa: F401
from ansible.module_utils.orchestrator_validation.renderers import (
    address_verifier as verifier,
)

pytestmark = pytest.mark.unit
LOGGER = logging.getLogger("address-verifier-test")


# ---------------------------------------------------------------------------
# Simulated system outputs
# ---------------------------------------------------------------------------

HEALTHY_IP_ADDR = """\
2: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc mq state UP
    inet6 fd00:1b::1/64 scope global manual preferred
       valid_lft forever preferred_lft forever
    inet6 fe80::1/64 scope link
       valid_lft forever preferred_lft forever
"""

TENTATIVE_IP_ADDR = """\
2: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044
    inet6 fd00:1b::1/64 scope global tentative
       valid_lft forever preferred_lft forever
"""

DADFAILED_IP_ADDR = """\
2: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044
    inet6 fd00:1b::1/64 scope global dadfailed
       valid_lft forever preferred_lft forever
"""

MISSING_ADDR_OUTPUT = """\
2: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044
    inet6 fe80::1/64 scope link
       valid_lft forever preferred_lft forever
"""

AUTONOMOUS_ADDR_OUTPUT = """\
2: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044
    inet6 fd00:1b::1/64 scope global manual preferred
       valid_lft forever preferred_lft forever
    inet6 fd00:1b::abcd:ef01/64 scope global dynamic autoconf
       valid_lft 604800sec preferred_lft 86400sec
    inet6 fd00:1b::9999:1234/64 scope global temporary mngtmpaddr
       valid_lft 604800sec preferred_lft 86400sec
    inet6 fe80::1/64 scope link
       valid_lft forever preferred_lft forever
"""

NO_DEFAULT_ROUTE = """\
fd00:1b::/64 dev ib0 proto kernel metric 256 pref medium
fe80::/64 dev ib0 proto kernel metric 256 pref medium
"""

HAS_DEFAULT_ROUTE = """\
default via fd00:1b::ffff dev ib0 proto static metric 100
fd00:1b::/64 dev ib0 proto kernel metric 256 pref medium
"""

PING_SUCCESS = """\
PING fd00:1b::2(fd00:1b::2) 56 data bytes
64 bytes from fd00:1b::2: icmp_seq=1 ttl=64 time=0.123 ms
64 bytes from fd00:1b::2: icmp_seq=2 ttl=64 time=0.098 ms
64 bytes from fd00:1b::2: icmp_seq=3 ttl=64 time=0.101 ms

--- fd00:1b::2 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2003ms
"""

PING_FAILURE = """\
PING fd00:1b::99(fd00:1b::99) 56 data bytes

--- fd00:1b::99 ping statistics ---
3 packets transmitted, 0 received, 100% packet loss, time 6007ms
"""

PRIVACY_DISABLED = "net.ipv6.conf.ib0.use_tempaddr = 0"
PRIVACY_ENABLED = "net.ipv6.conf.ib0.use_tempaddr = 2"


# ===================================================================
# TC-UT-008: Address-State Verifier
# ===================================================================

class TestAddressStateVerifier:
    """TC-UT-008: Address-state verification."""

    def test_healthy_address_found(self):
        """ORCH_UT_300: Expected address found with correct state."""
        result = verifier.verify_address_state(
            "fd00:1b::1", HEALTHY_IP_ADDR, "nid0001", "ib0", LOGGER
        )
        assert result["found"] is True
        assert result["errors"] == []
        assert result["dad_state"] == "ok"

    def test_tentative_address_flagged(self):
        """ORCH_UT_301: Tentative address is flagged as error."""
        result = verifier.verify_address_state(
            "fd00:1b::1", TENTATIVE_IP_ADDR, "nid0001", "ib0", LOGGER
        )
        assert result["found"] is True
        assert len(result["errors"]) >= 1
        assert result["dad_state"] == "tentative"

    def test_dadfailed_address_flagged(self):
        """ORCH_UT_302: DAD-failed address is flagged as error."""
        result = verifier.verify_address_state(
            "fd00:1b::1", DADFAILED_IP_ADDR, "nid0001", "ib0", LOGGER
        )
        assert result["found"] is True
        assert result["dad_state"] == "failed"

    def test_missing_address_error(self):
        """ORCH_UT_303: Missing address reports not found."""
        result = verifier.verify_address_state(
            "fd00:1b::1", MISSING_ADDR_OUTPUT, "nid0001", "ib0", LOGGER
        )
        assert result["found"] is False
        assert result["dad_state"] == "missing"

    def test_invalid_ipv6_input(self):
        """ORCH_UT_304: Invalid IPv6 address returns error."""
        result = verifier.verify_address_state(
            "not-valid", HEALTHY_IP_ADDR, "nid0001", "ib0", LOGGER
        )
        assert result["found"] is False
        assert result["dad_state"] == "invalid"


class TestAutonomousAddressDetector:
    """Autonomous address detection (AC-007)."""

    def test_no_autonomous_on_clean(self):
        """ORCH_UT_310: No autonomous addresses on clean interface."""
        result = verifier.detect_autonomous_addresses(
            HEALTHY_IP_ADDR, ["fd00:1b::1"], "ib0", LOGGER
        )
        assert result == []

    def test_slaac_detected(self):
        """ORCH_UT_311: SLAAC address detected as autonomous."""
        result = verifier.detect_autonomous_addresses(
            AUTONOMOUS_ADDR_OUTPUT, ["fd00:1b::1"], "ib0", LOGGER
        )
        assert len(result) >= 1
        types = {r["type"] for r in result}
        assert "slaac" in types or "privacy" in types

    def test_privacy_address_detected(self):
        """ORCH_UT_312: Privacy-generated address detected."""
        result = verifier.detect_autonomous_addresses(
            AUTONOMOUS_ADDR_OUTPUT, ["fd00:1b::1"], "ib0", LOGGER
        )
        assert any(r["type"] == "privacy" for r in result)

    def test_link_local_permitted(self):
        """ORCH_UT_313: Link-local addresses are NOT flagged."""
        result = verifier.detect_autonomous_addresses(
            HEALTHY_IP_ADDR, ["fd00:1b::1"], "ib0", LOGGER
        )
        assert not any(r["address"].startswith("fe80") for r in result)


class TestRouteVerifier:
    """Route verification (no IPoIB default route)."""

    def test_no_default_route_passes(self):
        """ORCH_UT_320: No default route passes verification."""
        errors = verifier.verify_no_default_route(
            NO_DEFAULT_ROUTE, "ib0", LOGGER
        )
        assert errors == []

    def test_default_route_detected(self):
        """ORCH_UT_321: Default route detected as error."""
        errors = verifier.verify_no_default_route(
            HAS_DEFAULT_ROUTE, "ib0", LOGGER
        )
        assert len(errors) >= 1
        assert any("default" in e.lower() for e in errors)


class TestPeerReachability:
    """Peer reachability verification."""

    def test_successful_ping(self):
        """ORCH_UT_330: Successful ping shows reachable."""
        result = verifier.parse_ping_result(PING_SUCCESS, 0)
        assert result["reachable"] is True
        assert result["packets_received"] == 3
        assert result["loss_pct"] == 0.0

    def test_failed_ping(self):
        """ORCH_UT_331: Failed ping shows unreachable."""
        result = verifier.parse_ping_result(PING_FAILURE, 1)
        assert result["reachable"] is False
        assert result["packets_received"] == 0
        assert result["loss_pct"] == 100.0

    def test_ping_command_format(self):
        """ORCH_UT_332: Ping command includes interface and IPv6."""
        cmd = verifier.build_peer_check_command(
            "fd00:1b::2", "ib0", count=3, timeout=5
        )
        assert "-6" in cmd
        assert "-I ib0" in cmd
        assert "fd00:1b::2" in cmd
        assert "-c 3" in cmd


class TestOpenSMNonRegression:
    """OpenSM non-regression verification (AC-008)."""

    def test_identical_snapshots(self):
        """ORCH_UT_340: Identical snapshots show no regression."""
        before = verifier.compute_opensm_snapshot(
            "config content", "lid/gid data", "pkey data"
        )
        after = verifier.compute_opensm_snapshot(
            "config content", "lid/gid data", "pkey data"
        )
        result = verifier.compare_opensm_snapshots(before, after, LOGGER)
        assert result["changed"] is False
        assert result["diffs"] == []

    def test_config_change_detected(self):
        """ORCH_UT_341: Config change detected as regression."""
        before = verifier.compute_opensm_snapshot(
            "config v1", "lid/gid data", "pkey data"
        )
        after = verifier.compute_opensm_snapshot(
            "config v2", "lid/gid data", "pkey data"
        )
        result = verifier.compare_opensm_snapshots(before, after, LOGGER)
        assert result["changed"] is True
        assert "config" in result["diffs"]

    def test_lid_gid_change_detected(self):
        """ORCH_UT_342: LID/GID change detected as regression."""
        before = verifier.compute_opensm_snapshot(
            "config", "lid-v1", "pkey"
        )
        after = verifier.compute_opensm_snapshot(
            "config", "lid-v2", "pkey"
        )
        result = verifier.compare_opensm_snapshots(before, after, LOGGER)
        assert result["changed"] is True
        assert "lid_gid" in result["diffs"]


class TestPrivacyVerification:
    """Privacy extension verification."""

    def test_privacy_disabled_passes(self):
        """ORCH_UT_350: use_tempaddr=0 passes verification."""
        result = verifier.verify_privacy_disabled(
            PRIVACY_DISABLED, "ib0", LOGGER
        )
        assert result["disabled"] is True
        assert result["value"] == 0
        assert result["error"] is None

    def test_privacy_enabled_fails(self):
        """ORCH_UT_351: use_tempaddr=2 fails verification."""
        result = verifier.verify_privacy_disabled(
            PRIVACY_ENABLED, "ib0", LOGGER
        )
        assert result["disabled"] is False
        assert result["value"] == 2
        assert result["error"] is not None


# ===================================================================
# Failure-mode reporting (AC-003)
# ===================================================================

class TestFailureModeReporting:
    """Failure-mode reporting: HEALTHY/DEGRADED/FAILED/RECOVERY."""

    def test_all_pass_healthy(self):
        """ORCH_UT_360: All checks pass → HEALTHY."""
        health = verifier.determine_health_status(
            address_errors=[],
            autonomous_addrs=[],
            route_errors=[],
            peer_result={"reachable": True},
            opensm_result={"changed": False, "diffs": []},
            privacy_result={"disabled": True},
            mode="dual-stack",
        )
        assert health["status"] == verifier.HealthStatus.HEALTHY

    def test_dual_stack_ipv6_failure_degraded(self):
        """ORCH_UT_361: Dual-stack IPv6 failure → DEGRADED_IPV6."""
        health = verifier.determine_health_status(
            address_errors=["address not found"],
            autonomous_addrs=[],
            route_errors=[],
            peer_result=None,
            opensm_result=None,
            privacy_result=None,
            mode="dual-stack",
        )
        assert health["status"] == verifier.HealthStatus.DEGRADED_IPV6
        assert "IPv4 operational" in health["corrective_action"]

    def test_ipv6_only_failure_failed(self):
        """ORCH_UT_362: IPv6-only failure → FAILED_IB_CONFIGURATION."""
        health = verifier.determine_health_status(
            address_errors=["address not found"],
            autonomous_addrs=[],
            route_errors=[],
            peer_result=None,
            opensm_result=None,
            privacy_result=None,
            mode="ipv6-only",
        )
        assert health["status"] == verifier.HealthStatus.FAILED_IB_CONFIGURATION
        assert "No IPv4 fallback" in health["corrective_action"]

    def test_opensm_regression_recovery_required(self):
        """ORCH_UT_363: OpenSM regression → RECOVERY_REQUIRED."""
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

    def test_route_failure_degraded(self):
        """ORCH_UT_364: Route failure in dual-stack → DEGRADED_IPV6."""
        health = verifier.determine_health_status(
            address_errors=[],
            autonomous_addrs=[],
            route_errors=["default route found"],
            peer_result=None,
            opensm_result=None,
            privacy_result=None,
            mode="dual-stack",
        )
        assert health["status"] == verifier.HealthStatus.DEGRADED_IPV6

    def test_peer_unreachable_degraded(self):
        """ORCH_UT_365: Peer unreachable in dual-stack → DEGRADED_IPV6."""
        health = verifier.determine_health_status(
            address_errors=[],
            autonomous_addrs=[],
            route_errors=[],
            peer_result={"reachable": False},
            opensm_result=None,
            privacy_result=None,
            mode="dual-stack",
        )
        assert health["status"] == verifier.HealthStatus.DEGRADED_IPV6

    def test_autonomous_addrs_degraded(self):
        """ORCH_UT_366: Autonomous addresses in dual-stack → DEGRADED_IPV6."""
        health = verifier.determine_health_status(
            address_errors=[],
            autonomous_addrs=[{"address": "fd00:1b::auto", "type": "slaac"}],
            route_errors=[],
            peer_result=None,
            opensm_result=None,
            privacy_result=None,
            mode="dual-stack",
        )
        assert health["status"] == verifier.HealthStatus.DEGRADED_IPV6


# ===================================================================
# Structured event logging
# ===================================================================

class TestStructuredEvents:
    """Structured [IB-IPv6] event logging (NFR-4)."""

    def test_event_has_required_fields(self):
        """ORCH_UT_370: Event has all required identity fields."""
        event = verifier.create_event(
            stage="address_state",
            result="HEALTHY",
            node_id="nid0001",
            interface_id="ib0",
            allocation_id="alloc-001",
            fabric_id="fabric1",
            rail_id="rail1",
            cluster_id="cluster1",
            message="All checks passed",
        )
        assert event["prefix"] == "[IB-IPv6]"
        assert event["stage"] == "address_state"
        assert event["result"] == "HEALTHY"
        assert event["node"] == "nid0001"
        assert event["interface"] == "ib0"
        assert event["allocation_id"] == "alloc-001"
        assert event["fabric"] == "fabric1"
        assert event["rail"] == "rail1"
        assert event["cluster"] == "cluster1"
        assert event["correlation_id"]

    def test_event_no_credentials(self):
        """ORCH_UT_371: Events never contain credential fields."""
        event = verifier.create_event(
            stage="test", result="OK", node_id="n1",
        )
        for key in event:
            assert "token" not in key.lower()
            assert "password" not in key.lower()
            assert "secret" not in key.lower()


# ===================================================================
# Full verification pipeline
# ===================================================================

class TestFullVerificationPipeline:
    """Full interface verification pipeline."""

    def test_healthy_interface(self):
        """ORCH_UT_380: Healthy interface passes all checks."""
        records = [{
            "address": "fd00:1b::1",
            "prefix_length": 64,
            "address_family": "ipv6",
        }]
        result = verifier.verify_interface(
            node_id="nid0001",
            interface_id="ib0",
            records=records,
            ip_addr_output=HEALTHY_IP_ADDR,
            ip_route_output=NO_DEFAULT_ROUTE,
            sysctl_output=PRIVACY_DISABLED,
            ping_output=PING_SUCCESS,
            ping_rc=0,
            logger=LOGGER,
        )
        assert result["health"]["status"] == verifier.HealthStatus.HEALTHY
        assert result["mode"] == "ipv6-only"

    def test_failed_interface_degraded(self):
        """ORCH_UT_381: Failed dual-stack interface reports DEGRADED_IPV6."""
        records = [
            {"address": "10.0.100.1", "prefix_length": 24, "address_family": "ipv4"},
            {"address": "fd00:1b::1", "prefix_length": 64, "address_family": "ipv6"},
        ]
        result = verifier.verify_interface(
            node_id="nid0001",
            interface_id="ib0",
            records=records,
            ip_addr_output=MISSING_ADDR_OUTPUT,
            ip_route_output=NO_DEFAULT_ROUTE,
            logger=LOGGER,
        )
        assert result["health"]["status"] == verifier.HealthStatus.DEGRADED_IPV6
        assert result["mode"] == "dual-stack"

    def test_ipv6_only_failure(self):
        """ORCH_UT_382: IPv6-only failure → FAILED_IB_CONFIGURATION."""
        records = [{
            "address": "fd00:1b::1",
            "prefix_length": 64,
            "address_family": "ipv6",
        }]
        result = verifier.verify_interface(
            node_id="nid0001",
            interface_id="ib0",
            records=records,
            ip_addr_output=MISSING_ADDR_OUTPUT,
            ip_route_output=NO_DEFAULT_ROUTE,
            logger=LOGGER,
        )
        assert result["health"]["status"] == verifier.HealthStatus.FAILED_IB_CONFIGURATION

    def test_opensm_regression_recovery(self):
        """ORCH_UT_383: OpenSM regression → RECOVERY_REQUIRED."""
        records = [{
            "address": "fd00:1b::1",
            "prefix_length": 64,
            "address_family": "ipv6",
        }]
        before = verifier.compute_opensm_snapshot("v1", "lid1", "pkey1")
        after = verifier.compute_opensm_snapshot("v2", "lid1", "pkey1")
        result = verifier.verify_interface(
            node_id="nid0001",
            interface_id="ib0",
            records=records,
            ip_addr_output=HEALTHY_IP_ADDR,
            ip_route_output=NO_DEFAULT_ROUTE,
            opensm_before=before,
            opensm_after=after,
            logger=LOGGER,
        )
        assert result["health"]["status"] == verifier.HealthStatus.RECOVERY_REQUIRED

    def test_autonomous_addresses_detected(self):
        """ORCH_UT_384: Autonomous addresses cause DEGRADED in dual-stack."""
        records = [
            {"address": "10.0.100.1", "prefix_length": 24, "address_family": "ipv4"},
            {"address": "fd00:1b::1", "prefix_length": 64, "address_family": "ipv6"},
        ]
        result = verifier.verify_interface(
            node_id="nid0001",
            interface_id="ib0",
            records=records,
            ip_addr_output=AUTONOMOUS_ADDR_OUTPUT,
            ip_route_output=NO_DEFAULT_ROUTE,
            logger=LOGGER,
        )
        assert result["health"]["status"] == verifier.HealthStatus.DEGRADED_IPV6
        assert len(result["autonomous"]) >= 1
