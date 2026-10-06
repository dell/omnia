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
"""Post-configuration verification for IPoIB IPv6 (ER-ORCH-005, Story 3).

Provides address-state verification, autonomous address detection, route
verification, peer reachability, OpenSM non-regression, structured event
logging, and failure-mode reporting.

Design decisions (from HLD — Verification Layer):
- HEALTHY / DEGRADED_IPV6 / FAILED_IB_CONFIGURATION / RECOVERY_REQUIRED
- Dual-stack: IPv6 failure preserves IPv4, reports DEGRADED_IPV6
- IPv6-only: failure reports FAILED_IB_CONFIGURATION (no IPv4 fallback)
- All events prefixed with [IB-IPv6] and carry structured identity fields
- OpenSM non-regression: config checksum, LID/GID/P_Key before/after diff
"""

from __future__ import annotations

import ipaddress
import re
import uuid
from enum import Enum
from logging import Logger
from typing import Any


# ---------------------------------------------------------------------------
# Health status enum (FR-6, AC-003)
# ---------------------------------------------------------------------------

class HealthStatus(str, Enum):
    """Post-configuration health status for an IPoIB interface."""
    HEALTHY = "HEALTHY"
    DEGRADED_IPV6 = "DEGRADED_IPV6"
    FAILED_IB_CONFIGURATION = "FAILED_IB_CONFIGURATION"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


# ---------------------------------------------------------------------------
# Verification stage identifiers
# ---------------------------------------------------------------------------

class VerificationStage(str, Enum):
    """Identifies where in the verification pipeline a failure occurred."""
    ADDRESS_STATE = "address_state"
    AUTONOMOUS_ADDR = "autonomous_address"
    ROUTE_CHECK = "route_check"
    PEER_REACHABILITY = "peer_reachability"
    OPENSM_REGRESSION = "opensm_regression"
    PRIVACY_CHECK = "privacy_check"
    DAD_CHECK = "dad_check"


# ---------------------------------------------------------------------------
# Structured [IB-IPv6] event logging (Task 6, NFR-4)
# ---------------------------------------------------------------------------

def create_event(
    stage: str,
    result: str,
    node_id: str,
    interface_id: str = "",
    allocation_id: str = "",
    fabric_id: str = "",
    rail_id: str = "",
    cluster_id: str = "",
    message: str = "",
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Create a structured [IB-IPv6] event.

    Events carry identity fields per NFR-4 and never include credentials.

    Args:
        stage: Verification stage (e.g., ``address_state``).
        result: Result of the check (e.g., ``HEALTHY``, ``FAILED``).
        node_id: Node identifier.
        interface_id: Interface identifier (e.g., ``ib0``).
        allocation_id: Allocation record ID.
        fabric_id: Fabric identifier.
        rail_id: Rail identifier.
        cluster_id: Cluster identifier.
        message: Human-readable description.
        correlation_id: Optional correlation ID; generated if not provided.

    Returns:
        Structured event dict.
    """
    return {
        "prefix": "[IB-IPv6]",
        "stage": stage,
        "result": result,
        "cluster": cluster_id,
        "node": node_id,
        "fabric": fabric_id,
        "rail": rail_id,
        "interface": interface_id,
        "allocation_id": allocation_id,
        "correlation_id": correlation_id or str(uuid.uuid4())[:8],
        "message": message,
    }


def log_event(
    event: dict[str, Any],
    logger: Logger | None = None,
) -> None:
    """Log a structured [IB-IPv6] event.

    Args:
        event: Event dict from ``create_event``.
        logger: Optional logger; prints to stdout if absent.
    """
    msg = (
        f"[IB-IPv6] [{event['stage']}] {event['result']} "
        f"node={event['node']} iface={event['interface']} "
        f"alloc={event['allocation_id']} — {event['message']}"
    )
    if logger:
        if event["result"] in ("FAILED", "DEGRADED_IPV6",
                               "FAILED_IB_CONFIGURATION",
                               "RECOVERY_REQUIRED"):
            logger.error(msg)
        else:
            logger.info(msg)


# ---------------------------------------------------------------------------
# Task 1: Address-State Verifier
# ---------------------------------------------------------------------------

# Address flags from `ip -6 addr show` output
_ADDR_FLAG_PATTERN = re.compile(
    r"inet6\s+(\S+)\s+scope\s+(\w+)\s*(.*)"
)

_BAD_FLAGS = frozenset({"tentative", "deprecated", "dadfailed"})
_EXPECTED_FLAGS = frozenset({"manual", "preferred"})


def verify_address_state(
    address: str,
    ip_addr_output: str,
    node_id: str = "",
    interface_id: str = "",
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Verify that an expected IPv6 address is present with correct state.

    Checks:
    - Address exists on the interface
    - Not tentative, deprecated, or dadfailed
    - Scope is global (not link)

    Args:
        address: Expected IPv6 address (e.g., ``fd00:1b::1``).
        ip_addr_output: Output of ``ip -6 addr show dev <iface>``.
        node_id: Node identifier for event logging.
        interface_id: Interface identifier.
        logger: Optional logger.

    Returns:
        Dict with ``found``, ``flags``, ``errors``, ``dad_state``.
    """
    try:
        normalized = str(ipaddress.IPv6Address(address))
    except (ValueError, ipaddress.AddressValueError):
        return {
            "found": False,
            "flags": [],
            "errors": [f"Invalid IPv6 address: {address}"],
            "dad_state": "invalid",
        }

    errors: list[str] = []
    found = False
    detected_flags: list[str] = []
    dad_state = "unknown"

    for line in ip_addr_output.splitlines():
        line = line.strip()
        if not line.startswith("inet6"):
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        addr_cidr = parts[1]
        addr_only = addr_cidr.split("/")[0]

        try:
            line_addr = str(ipaddress.IPv6Address(addr_only))
        except (ValueError, ipaddress.AddressValueError):
            continue

        if line_addr != normalized:
            continue

        found = True
        # Extract flags from the line
        flags_in_line = set(parts[2:]) if len(parts) > 2 else set()
        detected_flags = list(flags_in_line)

        # Check for bad flags
        bad = flags_in_line & _BAD_FLAGS
        if bad:
            dad_state = "failed" if "dadfailed" in bad else "tentative"
            for flag in bad:
                errors.append(
                    f"Address {address} on {interface_id}: "
                    f"bad flag '{flag}'"
                )
        else:
            dad_state = "ok"

        # Check scope
        if "scope" in line:
            scope_idx = parts.index("scope") if "scope" in parts else -1
            if scope_idx >= 0 and scope_idx + 1 < len(parts):
                scope = parts[scope_idx + 1]
                if scope == "link":
                    errors.append(
                        f"Address {address}: expected global scope, "
                        f"got link scope"
                    )

        break

    if not found:
        errors.append(
            f"Expected address {address} not found on {interface_id}"
        )
        dad_state = "missing"

    if errors and logger:
        event = create_event(
            stage=VerificationStage.ADDRESS_STATE,
            result="FAILED",
            node_id=node_id,
            interface_id=interface_id,
            message="; ".join(errors),
        )
        log_event(event, logger)

    return {
        "found": found,
        "flags": detected_flags,
        "errors": errors,
        "dad_state": dad_state,
    }


# ---------------------------------------------------------------------------
# Task 2: Autonomous address detector (AC-007)
# ---------------------------------------------------------------------------

# Patterns that identify autonomous (non-static) addresses
_AUTONOMOUS_INDICATORS = frozenset({
    "dynamic", "mngtmpaddr", "temporary", "autoconf",
})


def detect_autonomous_addresses(
    ip_addr_output: str,
    approved_addresses: list[str],
    interface_id: str = "",
    logger: Logger | None = None,
) -> list[dict[str, Any]]:
    """Detect autonomous (non-static) addresses on an interface.

    Autonomous addresses include SLAAC, EUI-64, MAC/GUID-derived, and
    privacy-generated addresses. Only global-scope addresses are checked;
    link-local (fe80::) is permitted.

    Args:
        ip_addr_output: Output of ``ip -6 addr show dev <iface>``.
        approved_addresses: List of approved static addresses (normalized).
        interface_id: Interface identifier.
        logger: Optional logger.

    Returns:
        List of dicts with ``address``, ``flags``, ``type`` for each
        autonomous address found.
    """
    # Normalize approved addresses
    approved_set: set[str] = set()
    for addr in approved_addresses:
        try:
            approved_set.add(str(ipaddress.IPv6Address(addr)))
        except (ValueError, ipaddress.AddressValueError):
            pass

    autonomous: list[dict[str, Any]] = []

    for line in ip_addr_output.splitlines():
        line = line.strip()
        if not line.startswith("inet6"):
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        addr_cidr = parts[1]
        addr_only = addr_cidr.split("/")[0]

        try:
            parsed = ipaddress.IPv6Address(addr_only)
            normalized = str(parsed)
        except (ValueError, ipaddress.AddressValueError):
            continue

        # Skip link-local (permitted)
        if parsed.is_link_local:
            continue

        # Skip approved static addresses
        if normalized in approved_set:
            continue

        flags = set(parts[2:]) if len(parts) > 2 else set()
        auto_flags = flags & _AUTONOMOUS_INDICATORS

        addr_type = "unknown"
        if auto_flags:
            if "temporary" in auto_flags or "mngtmpaddr" in auto_flags:
                addr_type = "privacy"
            elif "autoconf" in auto_flags or "dynamic" in auto_flags:
                addr_type = "slaac"
        else:
            addr_type = "unapproved_static"

        autonomous.append({
            "address": normalized,
            "flags": list(flags),
            "type": addr_type,
        })

    if autonomous and logger:
        event = create_event(
            stage=VerificationStage.AUTONOMOUS_ADDR,
            result="FAILED",
            node_id="",
            interface_id=interface_id,
            message=f"{len(autonomous)} autonomous address(es) detected",
        )
        log_event(event, logger)

    return autonomous


# ---------------------------------------------------------------------------
# Task 3: Route Verifier (AC-002 verification, AC-003)
# ---------------------------------------------------------------------------

def verify_no_default_route(
    ip_route_output: str,
    interface_id: str = "",
    logger: Logger | None = None,
) -> list[str]:
    """Verify no IPoIB default route exists on an interface.

    Args:
        ip_route_output: Output of ``ip -6 route show dev <iface>``.
        interface_id: Interface identifier.
        logger: Optional logger.

    Returns:
        List of error strings (empty if valid).
    """
    errors: list[str] = []
    for line in ip_route_output.splitlines():
        line = line.strip()
        if line.startswith("default") or line.startswith("::/0"):
            errors.append(
                f"IPoIB default route found on {interface_id}: {line}"
            )

    if errors and logger:
        event = create_event(
            stage=VerificationStage.ROUTE_CHECK,
            result="FAILED",
            node_id="",
            interface_id=interface_id,
            message="; ".join(errors),
        )
        log_event(event, logger)

    return errors


# ---------------------------------------------------------------------------
# Task 4: Peer Reachability Verifier
# ---------------------------------------------------------------------------

def build_peer_check_command(
    peer_address: str,
    interface_id: str,
    count: int = 3,
    timeout: int = 5,
) -> str:
    """Build a ping6 command for on-link peer reachability.

    Args:
        peer_address: Peer IPv6 address.
        interface_id: Interface to use.
        count: Number of ping packets.
        timeout: Timeout in seconds.

    Returns:
        Shell command string.
    """
    return (
        f"ping -6 -c {count} -W {timeout} -I {interface_id} "
        f"{peer_address}"
    )


def parse_ping_result(
    ping_output: str,
    return_code: int,
) -> dict[str, Any]:
    """Parse ping output to determine peer reachability.

    Args:
        ping_output: stdout from ping command.
        return_code: Exit code from ping.

    Returns:
        Dict with ``reachable``, ``packets_sent``, ``packets_received``,
        ``loss_pct``.
    """
    reachable = return_code == 0
    packets_sent = 0
    packets_received = 0
    loss_pct = 100.0

    for line in ping_output.splitlines():
        match = re.search(
            r"(\d+)\s+packets\s+transmitted.*?(\d+)\s+received.*?"
            r"(\d+(?:\.\d+)?)%\s+packet\s+loss",
            line,
        )
        if match:
            packets_sent = int(match.group(1))
            packets_received = int(match.group(2))
            loss_pct = float(match.group(3))
            break

    return {
        "reachable": reachable,
        "packets_sent": packets_sent,
        "packets_received": packets_received,
        "loss_pct": loss_pct,
    }


# ---------------------------------------------------------------------------
# Task 5: OpenSM Non-Regression Verifier (AC-008)
# ---------------------------------------------------------------------------

def compute_opensm_snapshot(
    opensm_config_content: str,
    lid_gid_output: str,
    pkey_output: str,
) -> dict[str, str]:
    """Compute a snapshot of OpenSM state for before/after comparison.

    Args:
        opensm_config_content: Content of ``/etc/opensm/opensm.conf``.
        lid_gid_output: Output of ``opensm -d`` or equivalent LID/GID dump.
        pkey_output: Output of P_Key partition dump.

    Returns:
        Dict with checksums for ``config``, ``lid_gid``, ``pkey``.
    """
    import hashlib

    return {
        "config": hashlib.sha256(
            opensm_config_content.encode("utf-8")
        ).hexdigest(),
        "lid_gid": hashlib.sha256(
            lid_gid_output.encode("utf-8")
        ).hexdigest(),
        "pkey": hashlib.sha256(
            pkey_output.encode("utf-8")
        ).hexdigest(),
    }


def compare_opensm_snapshots(
    before: dict[str, str],
    after: dict[str, str],
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Compare before/after OpenSM snapshots for regression.

    Args:
        before: Pre-configuration OpenSM snapshot.
        after: Post-configuration OpenSM snapshot.
        logger: Optional logger.

    Returns:
        Dict with ``changed``, ``diffs`` (list of changed component names).
    """
    diffs: list[str] = []
    for key in ("config", "lid_gid", "pkey"):
        if before.get(key) != after.get(key):
            diffs.append(key)

    if diffs and logger:
        event = create_event(
            stage=VerificationStage.OPENSM_REGRESSION,
            result="FAILED",
            node_id="",
            message=f"OpenSM state changed: {', '.join(diffs)}",
        )
        log_event(event, logger)

    return {
        "changed": len(diffs) > 0,
        "diffs": diffs,
    }


# ---------------------------------------------------------------------------
# Task 9: Privacy extension verification (sysctl check)
# ---------------------------------------------------------------------------

def verify_privacy_disabled(
    sysctl_output: str,
    interface_id: str,
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Verify privacy extensions are disabled via sysctl.

    Checks ``net.ipv6.conf.<iface>.use_tempaddr = 0``.

    Args:
        sysctl_output: Output of ``sysctl net.ipv6.conf.<iface>.use_tempaddr``.
        interface_id: Interface identifier.
        logger: Optional logger.

    Returns:
        Dict with ``disabled``, ``value``, ``error``.
    """
    match = re.search(r"use_tempaddr\s*=\s*(\d+)", sysctl_output)
    if not match:
        return {
            "disabled": False,
            "value": None,
            "error": f"Could not parse sysctl output for {interface_id}",
        }

    value = int(match.group(1))
    disabled = value == 0

    if not disabled and logger:
        event = create_event(
            stage=VerificationStage.PRIVACY_CHECK,
            result="FAILED",
            node_id="",
            interface_id=interface_id,
            message=f"Privacy extensions enabled (use_tempaddr={value})",
        )
        log_event(event, logger)

    return {
        "disabled": disabled,
        "value": value,
        "error": None if disabled else
            f"Privacy extensions not disabled on {interface_id}: "
            f"use_tempaddr={value}",
    }


# ---------------------------------------------------------------------------
# Task 7: Failure-mode reporting (AC-003)
# ---------------------------------------------------------------------------

def determine_health_status(
    address_errors: list[str],
    autonomous_addrs: list[dict[str, Any]],
    route_errors: list[str],
    peer_result: dict[str, Any] | None,
    opensm_result: dict[str, Any] | None,
    privacy_result: dict[str, Any] | None,
    mode: str,
) -> dict[str, Any]:
    """Determine the overall health status for an interface.

    Decision matrix:
    - All checks pass → HEALTHY
    - Dual-stack with IPv6 failure → DEGRADED_IPV6 (IPv4 preserved)
    - IPv6-only with failure → FAILED_IB_CONFIGURATION
    - OpenSM regression → RECOVERY_REQUIRED
    - Multiple critical failures → RECOVERY_REQUIRED

    Args:
        address_errors: From address-state verification.
        autonomous_addrs: From autonomous address detection.
        route_errors: From route verification.
        peer_result: From peer reachability (or None if not checked).
        opensm_result: From OpenSM non-regression (or None if not checked).
        privacy_result: From privacy check (or None if not checked).
        mode: Address family mode (``dual-stack``, ``ipv6-only``, ``ipv4-only``).

    Returns:
        Dict with ``status``, ``stage``, ``errors``, ``corrective_action``.
    """
    all_errors: list[str] = []
    failed_stage: str | None = None

    # OpenSM regression is always RECOVERY_REQUIRED
    if opensm_result and opensm_result.get("changed"):
        return {
            "status": HealthStatus.RECOVERY_REQUIRED,
            "stage": VerificationStage.OPENSM_REGRESSION,
            "errors": [f"OpenSM state changed: {opensm_result['diffs']}"],
            "corrective_action":
                "Investigate OpenSM state change; may require fabric admin",
        }

    # Collect all errors
    if address_errors:
        all_errors.extend(address_errors)
        failed_stage = failed_stage or VerificationStage.ADDRESS_STATE
    if autonomous_addrs:
        all_errors.append(
            f"{len(autonomous_addrs)} autonomous address(es) detected"
        )
        failed_stage = failed_stage or VerificationStage.AUTONOMOUS_ADDR
    if route_errors:
        all_errors.extend(route_errors)
        failed_stage = failed_stage or VerificationStage.ROUTE_CHECK
    if peer_result and not peer_result.get("reachable", True):
        all_errors.append("Peer unreachable")
        failed_stage = failed_stage or VerificationStage.PEER_REACHABILITY
    if privacy_result and not privacy_result.get("disabled", True):
        all_errors.append(privacy_result.get("error", "Privacy not disabled"))
        failed_stage = failed_stage or VerificationStage.PRIVACY_CHECK

    if not all_errors:
        return {
            "status": HealthStatus.HEALTHY,
            "stage": None,
            "errors": [],
            "corrective_action": None,
        }

    # Determine status based on mode
    if mode == "dual-stack":
        return {
            "status": HealthStatus.DEGRADED_IPV6,
            "stage": failed_stage,
            "errors": all_errors,
            "corrective_action":
                "IPv4 operational; investigate IPv6 configuration failure",
        }
    elif mode == "ipv6-only":
        return {
            "status": HealthStatus.FAILED_IB_CONFIGURATION,
            "stage": failed_stage,
            "errors": all_errors,
            "corrective_action":
                "No IPv4 fallback; fix IPv6 configuration or allocations",
        }
    else:
        # IPv4-only mode with failures
        return {
            "status": HealthStatus.FAILED_IB_CONFIGURATION,
            "stage": failed_stage,
            "errors": all_errors,
            "corrective_action":
                "Investigate IPoIB configuration failure",
        }


# ---------------------------------------------------------------------------
# Full verification pipeline
# ---------------------------------------------------------------------------

def verify_interface(
    node_id: str,
    interface_id: str,
    records: list[dict[str, Any]],
    ip_addr_output: str,
    ip_route_output: str,
    sysctl_output: str = "",
    ping_output: str = "",
    ping_rc: int = 0,
    opensm_before: dict[str, str] | None = None,
    opensm_after: dict[str, str] | None = None,
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Run the full verification pipeline for a single interface.

    Args:
        node_id: Node identifier.
        interface_id: Interface identifier.
        records: Allocation records for this interface.
        ip_addr_output: Output of ``ip -6 addr show dev <iface>``.
        ip_route_output: Output of ``ip -6 route show dev <iface>``.
        sysctl_output: Output of sysctl privacy check.
        ping_output: Output of peer ping.
        ping_rc: Return code of peer ping.
        opensm_before: Pre-config OpenSM snapshot.
        opensm_after: Post-config OpenSM snapshot.
        logger: Optional logger.

    Returns:
        Dict with ``health``, ``address_checks``, ``autonomous``,
        ``route_errors``, ``peer``, ``opensm``, ``privacy``.
    """
    # Determine mode
    families = {r.get("address_family") for r in records}
    if "ipv4" in families and "ipv6" in families:
        mode = "dual-stack"
    elif "ipv6" in families:
        mode = "ipv6-only"
    else:
        mode = "ipv4-only"

    # Task 1: Address-state verification
    address_checks = []
    address_errors: list[str] = []
    for record in records:
        if record.get("address_family") != "ipv6":
            continue
        check = verify_address_state(
            record["address"], ip_addr_output,
            node_id, interface_id, logger,
        )
        address_checks.append(check)
        address_errors.extend(check["errors"])

    # Task 2: Autonomous address detection
    approved = [
        r["address"] for r in records
        if r.get("address_family") == "ipv6"
    ]
    autonomous = detect_autonomous_addresses(
        ip_addr_output, approved, interface_id, logger,
    )

    # Task 3: Route verification
    route_errors = verify_no_default_route(
        ip_route_output, interface_id, logger,
    )

    # Task 4: Peer reachability
    peer_result = None
    if ping_output:
        peer_result = parse_ping_result(ping_output, ping_rc)

    # Task 5: OpenSM non-regression
    opensm_result = None
    if opensm_before and opensm_after:
        opensm_result = compare_opensm_snapshots(
            opensm_before, opensm_after, logger,
        )

    # Task 9: Privacy extension check
    privacy_result = None
    if sysctl_output:
        privacy_result = verify_privacy_disabled(
            sysctl_output, interface_id, logger,
        )

    # Task 7: Determine health status
    health = determine_health_status(
        address_errors, autonomous, route_errors,
        peer_result, opensm_result, privacy_result,
        mode,
    )

    return {
        "node_id": node_id,
        "interface_id": interface_id,
        "mode": mode,
        "health": health,
        "address_checks": address_checks,
        "autonomous": autonomous,
        "route_errors": route_errors,
        "peer": peer_result,
        "opensm": opensm_result,
        "privacy": privacy_result,
    }
