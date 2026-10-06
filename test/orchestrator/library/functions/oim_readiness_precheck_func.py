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

"""Read-only OIM hardware and network readiness checks.

These checkers validate the contracts covered by the Omnia 2.2 automation
prerequisite runner but not yet verified by the existing 2.3 precheck FVT.
Every function is read-only and never mutates the target environment.
"""

import posixpath
import re
from typing import Any

from omnia_auto import run_on_host

from ..vars.precheck_vars import (
    INTERNET_CHECK_HOSTS,
    OIM_MIN_CPU_CORES,
    OIM_MIN_DISK_GB,
    OIM_MIN_MEMORY_GB,
    OIM_READINESS_COMMANDS,
)
from ._prepare_helpers import prepare_result, read_yaml_mapping
from .project_func import resolve_target_input_project_path

_IPV4_CIDR = re.compile(r"\binet\s+([0-9.]+/[0-9]+)\b")


# ── helpers ─────────────────────────────────────────────────────────


def _admin_network(host) -> dict[str, Any]:
    """Return the admin_network mapping from network_spec.yml."""
    path = posixpath.join(
        resolve_target_input_project_path(host), "network_spec.yml"
    )
    spec = read_yaml_mapping(host, path)
    networks = spec.get("Networks", spec.get("networks", []))
    if not isinstance(networks, list):
        raise TypeError("network_spec.yml Networks must be a list")
    for network in networks:
        if isinstance(network, dict) and isinstance(
            network.get("admin_network"), dict
        ):
            return network["admin_network"]
    raise ValueError("network_spec.yml does not define admin_network")


# ── hardware checks ────────────────────────────────────────────────


def check_oim_cpu_threshold(host, *, min_cores: int = 0) -> dict[str, Any]:
    """Verify OIM CPU core count meets the configured minimum."""
    threshold = min_cores or OIM_MIN_CPU_CORES
    try:
        result = run_on_host(host, OIM_READINESS_COMMANDS["cpu_cores"])
    except (OSError, RuntimeError) as exc:
        return prepare_result(False, "Unable to query CPU cores", [], str(exc))

    cores = int(result.stdout.strip()) if result.rc == 0 else 0
    ok = cores >= threshold
    fields = [
        ("CPU cores detected", cores),
        ("Minimum required", threshold),
        ("CPU threshold met", "yes" if ok else "NO"),
    ]
    error = ""
    if not ok:
        error = (
            f"CPU cores ({cores}) below minimum ({threshold}). "
            "Upgrade hardware or adjust min_cores in test configuration."
        )
    return prepare_result(ok, "OIM CPU threshold checked", fields, error)


def check_oim_memory_threshold(
    host, *, min_memory_gb: int = 0
) -> dict[str, Any]:
    """Verify OIM memory meets the configured minimum."""
    threshold = min_memory_gb or OIM_MIN_MEMORY_GB
    try:
        result = run_on_host(host, OIM_READINESS_COMMANDS["memory_kb"])
    except (OSError, RuntimeError) as exc:
        return prepare_result(False, "Unable to query memory", [], str(exc))

    mem_kb = int(result.stdout.strip()) if result.rc == 0 else 0
    mem_gb = mem_kb // (1024 * 1024)
    ok = mem_gb >= threshold
    fields = [
        ("Memory detected", f"{mem_gb} GB"),
        ("Minimum required", f"{threshold} GB"),
        ("Memory threshold met", "yes" if ok else "NO"),
    ]
    error = ""
    if not ok:
        error = (
            f"Memory ({mem_gb} GB) below minimum ({threshold} GB). "
            "Upgrade hardware or adjust min_memory_gb in test configuration."
        )
    return prepare_result(ok, "OIM memory threshold checked", fields, error)


def check_oim_disk_threshold(
    host, *, min_disk_gb: int = 0
) -> dict[str, Any]:
    """Verify OIM root filesystem meets the configured minimum."""
    threshold = min_disk_gb or OIM_MIN_DISK_GB
    try:
        result = run_on_host(host, OIM_READINESS_COMMANDS["disk_gb"])
    except (OSError, RuntimeError) as exc:
        return prepare_result(
            False, "Unable to query root disk size", [], str(exc)
        )

    disk_gb = int(result.stdout.strip()) if result.rc == 0 else 0
    ok = disk_gb >= threshold
    fields = [
        ("Root filesystem size", f"{disk_gb} GB"),
        ("Minimum required", f"{threshold} GB"),
        ("Disk threshold met", "yes" if ok else "NO"),
    ]
    error = ""
    if not ok:
        error = (
            f"Root disk ({disk_gb} GB) below minimum ({threshold} GB). "
            "Expand root filesystem or adjust min_disk_gb in test configuration."
        )
    return prepare_result(ok, "OIM disk threshold checked", fields, error)


# ── network checks ─────────────────────────────────────────────────


def check_oim_pxe_nic_present(host) -> dict[str, Any]:
    """Verify the configured admin NIC exists and is operationally UP."""
    try:
        admin = _admin_network(host)
        nic_name = str(admin.get("oim_nic_name") or "").strip()
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(
            False, "Unable to resolve admin NIC", [], str(exc)
        )

    if not nic_name:
        return prepare_result(
            False,
            "Admin NIC not configured",
            [("oim_nic_name", "not set")],
            "network_spec.yml admin_network.oim_nic_name is empty",
        )

    result = run_on_host(
        host, OIM_READINESS_COMMANDS["nic_operstate"], nic_name
    )
    state = result.stdout.strip() if result.rc == 0 else ""
    exists = result.rc == 0 and bool(state)
    is_up = state == "up"
    fields = [
        ("Admin NIC", nic_name),
        ("Interface exists", "yes" if exists else "NO"),
        ("Operational state", state or "not found"),
        ("State is UP", "yes" if is_up else "NO"),
    ]
    if not exists:
        return prepare_result(
            False,
            "Admin NIC state checked",
            fields,
            f"Interface {nic_name} not found in /sys/class/net/",
        )
    if not is_up:
        return prepare_result(
            False,
            "Admin NIC state checked",
            fields,
            f"Interface {nic_name} is {state!r}, expected 'up'. "
            f"Check cabling and run: ip link set {nic_name} up",
        )
    return prepare_result(True, "Admin NIC state checked", fields)


def check_oim_public_nic_present(host) -> dict[str, Any]:
    """Verify public/default-route interface exists and is UP.

    The public interface is derived from the default IPv4 route. If no
    default route exists, the check passes as not-applicable (air-gapped
    or PXE-only environments do not require a public interface).
    """
    try:
        result = run_on_host(
            host, "ip -4 route show default 2>/dev/null | head -1"
        )
    except (OSError, RuntimeError) as exc:
        return prepare_result(
            False, "Unable to query default route", [], str(exc)
        )

    line = result.stdout.strip()
    if not line:
        return prepare_result(
            True,
            "No default IPv4 route; public NIC check not applicable",
            [("Default route", "none"), ("Public NIC check", "skipped")],
        )

    parts = line.split()
    nic_name = ""
    for i, token in enumerate(parts):
        if token == "dev" and i + 1 < len(parts):
            nic_name = parts[i + 1]
            break

    if not nic_name:
        return prepare_result(
            False,
            "Default route present but no device parsed",
            [("Default route", line)],
            "Could not extract device from default route",
        )

    state_result = run_on_host(
        host, OIM_READINESS_COMMANDS["nic_operstate"], nic_name
    )
    state = state_result.stdout.strip() if state_result.rc == 0 else ""
    is_up = state == "up"
    fields = [
        ("Public NIC", nic_name),
        ("Default route", line),
        ("Operational state", state or "not found"),
        ("State is UP", "yes" if is_up else "NO"),
    ]
    if not is_up:
        return prepare_result(
            False,
            "Public NIC state checked",
            fields,
            f"Public interface {nic_name} is {state!r}, expected 'up'",
        )
    return prepare_result(True, "Public NIC state checked", fields)


def check_oim_pxe_nic_ipv4(host) -> dict[str, Any]:
    """Verify the admin NIC has the expected IPv4 address assigned."""
    try:
        admin = _admin_network(host)
        nic_name = str(admin.get("oim_nic_name") or "").strip()
        expected_ip = str(admin.get("primary_oim_admin_ip") or "").strip()
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(
            False, "Unable to resolve admin NIC config", [], str(exc)
        )

    if not nic_name or not expected_ip:
        return prepare_result(
            False,
            "Admin NIC or IP not configured",
            [("oim_nic_name", nic_name or "not set"),
             ("primary_oim_admin_ip", expected_ip or "not set")],
            "network_spec.yml admin_network.oim_nic_name or "
            "primary_oim_admin_ip is empty",
        )

    result = run_on_host(
        host, OIM_READINESS_COMMANDS["nic_ipv4"], nic_name
    )
    cidrs = _IPV4_CIDR.findall(result.stdout) if result.rc == 0 else []
    addresses = [cidr.split("/")[0] for cidr in cidrs]
    assigned = expected_ip in addresses
    fields = [
        ("Admin NIC", nic_name),
        ("Expected IPv4", expected_ip),
        ("Assigned IPv4 addresses", ", ".join(cidrs) or "none"),
        ("Expected IP assigned", "yes" if assigned else "NO"),
    ]
    error = ""
    if not assigned:
        error = (
            f"Expected IP {expected_ip} not found on {nic_name}. "
            f"Assigned addresses: {', '.join(cidrs) or 'none'}"
        )
    return prepare_result(
        assigned, "Admin NIC IPv4 assignment checked", fields, error
    )


def check_oim_pxe_public_overlap(
    host, *, nic_name: str = ""
) -> dict[str, Any]:
    """Detect when the PXE NIC and public-route NIC are the same interface."""
    try:
        admin = _admin_network(host)
        pxe_nic = nic_name or str(admin.get("oim_nic_name") or "").strip()
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(
            False, "Unable to resolve admin NIC", [], str(exc)
        )

    if not pxe_nic:
        return prepare_result(
            True,
            "No PXE NIC configured; overlap check not applicable",
            [("PXE NIC", "not configured")],
        )

    route_result = run_on_host(
        host, "ip -4 route show default 2>/dev/null | head -1"
    )
    route_line = route_result.stdout.strip()
    public_nic = ""
    if route_line:
        parts = route_line.split()
        for i, token in enumerate(parts):
            if token == "dev" and i + 1 < len(parts):
                public_nic = parts[i + 1]
                break

    if not public_nic:
        return prepare_result(
            True,
            "No default route; PXE/public overlap not applicable",
            [("PXE NIC", pxe_nic), ("Public NIC", "none (no default route)")],
        )

    same_nic = pxe_nic == public_nic
    fields = [
        ("PXE NIC", pxe_nic),
        ("Public NIC", public_nic),
        ("Same interface", "YES (overlap)" if same_nic else "no"),
    ]
    error = ""
    if same_nic:
        error = (
            f"PXE and public traffic share interface {pxe_nic}. "
            "This is a misconfiguration: PXE should be isolated."
        )
    return prepare_result(
        not same_nic,
        "PXE / public NIC overlap checked",
        fields,
        error,
    )


# ── prerequisite checks ────────────────────────────────────────────


def check_oim_ssh_preflight(host) -> dict[str, Any]:
    """Verify passwordless SSH from OIM to a configured target node.

    Uses the first mapped node from the PXE mapping CSV as the target.
    Skips if no mapping is configured or no nodes are present.
    """
    try:
        input_dir = resolve_target_input_project_path(host)
        config = read_yaml_mapping(
            host, posixpath.join(input_dir, "orchestrator_config.yml")
        )
        mapping_path = str(
            config.get("pxe_mapping_file_path")
            or posixpath.join(input_dir, "pxe_mapping_file.csv")
        ).strip()
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(
            False, "Unable to resolve SSH targets", [], str(exc)
        )

    if not host.file(mapping_path).is_file:
        return prepare_result(
            True,
            "No PXE mapping file; SSH preflight skipped",
            [("PXE mapping", "not found"), ("SSH preflight", "skipped")],
        )

    # Read the first ADMIN_IP from the mapping
    raw = run_on_host(host, "head -2 %s", mapping_path)
    lines = raw.stdout.strip().split("\n") if raw.rc == 0 else []
    if len(lines) < 2:
        return prepare_result(
            True,
            "PXE mapping has no data rows; SSH preflight skipped",
            [("PXE mapping", mapping_path), ("SSH preflight", "skipped")],
        )

    import csv
    import io

    reader = csv.DictReader(io.StringIO(raw.stdout))
    row = next(reader, None)
    if not row or not row.get("ADMIN_IP", "").strip():
        return prepare_result(
            True,
            "No ADMIN_IP in PXE mapping; SSH preflight skipped",
            [("PXE mapping", mapping_path), ("SSH preflight", "skipped")],
        )

    target = row["ADMIN_IP"].strip()
    ssh_result = run_on_host(
        host, OIM_READINESS_COMMANDS["ssh_check"], target
    )
    success = ssh_result.rc == 0 and "root" in ssh_result.stdout
    fields = [
        ("Target node", target),
        ("SSH exit code", ssh_result.rc),
        ("whoami output", ssh_result.stdout.strip() or "empty"),
        ("SSH successful", "yes" if success else "NO"),
    ]
    error = ""
    if not success:
        error = (
            f"SSH to {target} failed (rc={ssh_result.rc}). "
            "Verify passwordless SSH keys are deployed."
        )
    return prepare_result(
        success, "OIM SSH preflight checked", fields, error
    )


def check_oim_internet_reachability(
    host, *, require_internet: bool = True
) -> dict[str, Any]:
    """Verify internet reachability via ICMP ping.

    When require_internet is False (air-gapped mode), the check passes
    regardless of ping results.
    """
    reachable_host = ""
    for dns in INTERNET_CHECK_HOSTS:
        result = run_on_host(
            host, OIM_READINESS_COMMANDS["internet_ping"], dns
        )
        if result.rc == 0:
            reachable_host = dns
            break

    reachable = bool(reachable_host)
    fields = [
        ("Internet required", "yes" if require_internet else "no (air-gapped)"),
        ("Hosts probed", ", ".join(INTERNET_CHECK_HOSTS)),
        ("Reachable via", reachable_host or "none"),
        ("Internet available", "yes" if reachable else "NO"),
    ]

    if not require_internet:
        return prepare_result(
            True,
            "Air-gapped mode; internet check passed regardless",
            fields,
        )

    error = ""
    if not reachable:
        error = (
            "No internet connectivity. Failed to ping: "
            + ", ".join(INTERNET_CHECK_HOSTS)
            + ". Check public NIC, gateway, and DNS configuration."
        )
    return prepare_result(
        reachable, "Internet reachability checked", fields, error
    )


def check_oim_os_version(
    host, *, expected_id: str = "rhel", expected_version: str = "10"
) -> dict[str, Any]:
    """Verify OIM OS matches the expected distribution and version."""
    try:
        result = run_on_host(host, OIM_READINESS_COMMANDS["os_release"])
    except (OSError, RuntimeError) as exc:
        return prepare_result(
            False, "Unable to read /etc/os-release", [], str(exc)
        )

    actual_id = ""
    actual_version = ""
    for line in result.stdout.strip().split("\n"):
        line = line.strip().strip('"').strip("'")
        if line.startswith("ID="):
            actual_id = line.split("=", 1)[1].strip().strip('"').strip("'")
        elif line.startswith("VERSION_ID="):
            actual_version = (
                line.split("=", 1)[1].strip().strip('"').strip("'")
            )

    id_ok = actual_id.lower().startswith(expected_id.lower())
    ver_ok = actual_version.startswith(expected_version)
    ok = id_ok and ver_ok
    fields = [
        ("Expected OS", expected_id),
        ("Actual OS", actual_id or "unknown"),
        ("OS match", "yes" if id_ok else "NO"),
        ("Expected version prefix", expected_version),
        ("Actual version", actual_version or "unknown"),
        ("Version match", "yes" if ver_ok else "NO"),
    ]
    failures = []
    if not id_ok:
        failures.append(f"OS {actual_id!r} != {expected_id!r}")
    if not ver_ok:
        failures.append(f"version {actual_version!r} != {expected_version!r}")
    return prepare_result(
        ok,
        "OIM OS version checked",
        fields,
        "; ".join(failures),
    )
