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

"""Minimal OS validation after PXE boot.

Verifies that OS-only provisioned nodes have the correct base packages,
required services, monitoring agents, and do NOT contain workload-specific
software (Slurm, Kubernetes, container runtimes, GPU drivers, MPI stacks).
"""

import re
from typing import Any

from ..vars.pxeboot_vars import PXEBOOT_COMMANDS
from ._pxeboot_helpers import (
    load_runtime_context,
    remote_command,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import optional_skip as _skip


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OS_PREFIX = "os_"

BASE_PACKAGES = [
    "kernel",
    "systemd",
    "NetworkManager",
    "openssh-server",
    "chrony",
    "dnf",
]

LDMS_PACKAGES = [
    "ovis-ldms",
]

REQUIRED_SERVICES = [
    "sshd",
    "chronyd",
    "NetworkManager",
]

EXCLUDED_PACKAGE_PATTERNS = {
    "slurm": "Slurm",
    "kube|k8s|kubernetes": "Kubernetes",
    "docker|podman|containerd": "Container runtime",
    "mlnx|ofed|doca": "DOCA-OFED",
    "cuda|nvidia-driver": "CUDA/GPU driver",
    "openmpi|mpich": "MPI",
}

EXCLUDED_SERVICES = [
    "slurmd",
    "slurmctld",
    "slurmdbd",
    "slurmrestd",
    "munge",
    "kubelet",
    "docker",
    "podman",
    "containerd",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _os_rows(context: dict[str, Any]) -> list[dict[str, str]]:
    """Select mapping rows for OS-only functional groups."""
    return [
        row for row in context["rows"]
        if row.get("EXPECTED_FUNCTIONAL_GROUP", "").startswith(OS_PREFIX)
    ]


# ---------------------------------------------------------------------------
# Public check functions
# ---------------------------------------------------------------------------


def check_minimal_os_base_packages(host):
    """Verify base OS packages are installed on all OS-only nodes."""
    summary = "Minimal OS base packages"
    try:
        context = load_runtime_context(host)
        rows = _os_rows(context)
        if not rows:
            return _skip(summary, "No OS-only nodes mapped")

        outcomes = {}
        for row in rows:
            missing = []
            for package in BASE_PACKAGES:
                cmd = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["minimal_os_rpm_check"] % package,
                )
                if cmd.rc != 0:
                    missing.append(package)
            key = row["HOSTNAME"]
            if missing:
                outcomes[key] = (False, f"missing: {', '.join(missing)}")
            else:
                outcomes[key] = (
                    True,
                    f"all {len(BASE_PACKAGES)} packages present",
                )

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("OS nodes", len(rows))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Base packages missing on: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_minimal_os_ldms_packages(host):
    """Verify LDMS monitoring packages and binary on OS-only nodes."""
    summary = "Minimal OS LDMS packages"
    try:
        context = load_runtime_context(host)
        rows = _os_rows(context)
        if not rows:
            return _skip(summary, "No OS-only nodes mapped")

        outcomes = {}
        for row in rows:
            missing = []
            for package in LDMS_PACKAGES:
                cmd = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["minimal_os_rpm_check"] % package,
                )
                if cmd.rc != 0:
                    missing.append(package)
            binary_cmd = remote_command(
                host, row,
                PXEBOOT_COMMANDS["minimal_os_binary_check"],
            )
            binary_ok = binary_cmd.rc == 0
            key = row["HOSTNAME"]
            if missing:
                outcomes[key] = (False, f"missing: {', '.join(missing)}")
            elif not binary_ok:
                outcomes[key] = (False, "ldmsd binary not found")
            else:
                outcomes[key] = (True, "ovis-ldms installed, ldmsd present")

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("OS nodes", len(rows))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "LDMS missing on: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_minimal_os_required_services(host):
    """Verify required services are active on all OS-only nodes."""
    summary = "Minimal OS required services"
    try:
        context = load_runtime_context(host)
        rows = _os_rows(context)
        if not rows:
            return _skip(summary, "No OS-only nodes mapped")

        outcomes = {}
        for row in rows:
            not_running = []
            for service in REQUIRED_SERVICES:
                cmd = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["node_services"] % service,
                )
                if cmd.rc != 0 or "active" not in cmd.stdout.strip():
                    not_running.append(service)
            key = row["HOSTNAME"]
            if not_running:
                outcomes[key] = (
                    False,
                    f"not active: {', '.join(not_running)}",
                )
            else:
                outcomes[key] = (
                    True,
                    f"all {len(REQUIRED_SERVICES)} services active",
                )

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("OS nodes", len(rows))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Services not active on: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_minimal_os_ldms_service_state(host):
    """Verify LDMS service is installed but NOT running at handoff."""
    summary = "Minimal OS LDMS service state"
    try:
        context = load_runtime_context(host)
        rows = _os_rows(context)
        if not rows:
            return _skip(summary, "No OS-only nodes mapped")

        outcomes = {}
        for row in rows:
            cmd = remote_command(
                host, row,
                PXEBOOT_COMMANDS["node_services"] % "ldmsd",
            )
            key = row["HOSTNAME"]
            output = cmd.stdout.strip().lower()
            if cmd.rc > 4:
                # rc > 4 indicates transport/SSH failure, not systemctl state
                outcomes[key] = (
                    False,
                    f"SSH or command failure (rc={cmd.rc})",
                )
            elif output in ("inactive", "dead", "unknown") or cmd.rc == 3:
                outcomes[key] = (True, "ldmsd inactive (expected)")
            elif output == "active":
                outcomes[key] = (
                    False,
                    "ldmsd is active (should be inactive at handoff)",
                )
            else:
                outcomes[key] = (
                    False,
                    f"unexpected state: {output} (rc={cmd.rc})",
                )

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("OS nodes", len(rows))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "LDMS active on: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_minimal_os_excluded_packages(host):
    """Verify workload-specific packages are NOT installed on OS-only nodes."""
    summary = "Minimal OS excluded packages"
    try:
        context = load_runtime_context(host)
        rows = _os_rows(context)
        if not rows:
            return _skip(summary, "No OS-only nodes mapped")

        outcomes = {}
        for row in rows:
            found = []
            ssh_failed = False
            for pattern, label in EXCLUDED_PACKAGE_PATTERNS.items():
                cmd = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["minimal_os_rpm_query_grep"] % pattern,
                )
                if cmd.rc > 1:
                    # rc > 1 indicates SSH/transport failure, not grep result
                    ssh_failed = True
                    break
                if cmd.rc == 0 and cmd.stdout.strip():
                    found.append(label)
            key = row["HOSTNAME"]
            if ssh_failed:
                outcomes[key] = (
                    False,
                    f"SSH or command failure (rc={cmd.rc})",
                )
            elif found:
                outcomes[key] = (
                    False,
                    f"found: {', '.join(found)}",
                )
            else:
                outcomes[key] = (True, "no excluded packages")

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("OS nodes", len(rows))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Excluded packages found on: " + ", ".join(failed)
            if failed
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_minimal_os_excluded_services(host):
    """Verify workload-specific services are NOT active on OS-only nodes."""
    summary = "Minimal OS excluded services"
    try:
        context = load_runtime_context(host)
        rows = _os_rows(context)
        if not rows:
            return _skip(summary, "No OS-only nodes mapped")

        outcomes = {}
        for row in rows:
            active = []
            ssh_failed = False
            for service in EXCLUDED_SERVICES:
                cmd = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["node_services"] % service,
                )
                if cmd.rc > 4:
                    # rc > 4 indicates SSH/transport failure
                    ssh_failed = True
                    break
                if cmd.rc == 0 and cmd.stdout.strip().lower() == "active":
                    active.append(service)
            key = row["HOSTNAME"]
            if ssh_failed:
                outcomes[key] = (
                    False,
                    f"SSH or command failure (rc={cmd.rc})",
                )
            elif active:
                outcomes[key] = (
                    False,
                    f"active: {', '.join(active)}",
                )
            else:
                outcomes[key] = (True, "no excluded services active")

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("OS nodes", len(rows))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Excluded services active on: " + ", ".join(failed)
            if failed
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_minimal_os_package_manager(host):
    """Verify package manager (dnf/yum) is functional on OS-only nodes."""
    summary = "Minimal OS package manager"
    try:
        context = load_runtime_context(host)
        rows = _os_rows(context)
        if not rows:
            return _skip(summary, "No OS-only nodes mapped")

        outcomes = {}
        for row in rows:
            cmd = remote_command(
                host, row,
                PXEBOOT_COMMANDS["minimal_os_pkg_mgr_check"],
            )
            key = row["HOSTNAME"]
            if cmd.rc == 0:
                outcomes[key] = (True, "package manager functional")
            else:
                outcomes[key] = (False, "package manager failed")

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("OS nodes", len(rows))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Package manager broken on: " + ", ".join(failed)
            if failed
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_minimal_os_kernel_version(host):
    """Verify kernel version is consistent across OS-only nodes per FG."""
    summary = "Minimal OS kernel version"
    try:
        context = load_runtime_context(host)
        rows = _os_rows(context)
        if not rows:
            return _skip(summary, "No OS-only nodes mapped")

        outcomes = {}
        kernels_by_fg: dict[str, list[str]] = {}
        for row in rows:
            cmd = remote_command(
                host, row,
                PXEBOOT_COMMANDS["minimal_os_kernel_version"],
            )
            key = row["HOSTNAME"]
            kernel = cmd.stdout.strip()
            if not kernel:
                outcomes[key] = (False, "could not read kernel version")
                continue
            fg = row.get("EXPECTED_FUNCTIONAL_GROUP", "unknown")
            kernels_by_fg.setdefault(fg, []).append(kernel)
            outcomes[key] = (True, kernel)

        for fg, versions in kernels_by_fg.items():
            unique = set(versions)
            if len(unique) > 1:
                for key, (ok, detail) in list(outcomes.items()):
                    if ok and detail in versions:
                        outcomes[key] = (
                            False,
                            f"inconsistent kernel in {fg}: {detail} "
                            f"(found {len(unique)} versions)",
                        )

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("OS nodes", len(rows))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Kernel issues on: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def _parse_ip_addresses(ip_output: str) -> set[str]:
    """Extract exact IP addresses from ``ip -o addr show`` output.

    Each line has the form:
        ``<idx> <dev> <family> <addr>/<prefix> ...``
    Returns a set of bare IP addresses (no CIDR prefix).
    """
    addresses: set[str] = set()
    for line in ip_output.strip().split("\n"):
        parts = line.split()
        # ip -o addr: field 0=index, 1=iface, 2=family, 3=addr/prefix
        if len(parts) >= 4:
            addr_field = parts[3]
            # Strip CIDR prefix (e.g. "10.0.0.10/24" -> "10.0.0.10")
            bare_ip = addr_field.split("/")[0]
            if bare_ip:
                addresses.add(bare_ip)
    return addresses


def check_minimal_os_network_identity(host):
    """Verify admin IP is configured on all OS-only nodes.

    Parses ``ip -o addr show`` output and compares exact normalised
    IP addresses, preventing ``10.0.0.1`` from matching ``10.0.0.10/24``.
    """
    summary = "Minimal OS network identity"
    try:
        context = load_runtime_context(host)
        rows = _os_rows(context)
        if not rows:
            return _skip(summary, "No OS-only nodes mapped")

        outcomes = {}
        for row in rows:
            expected_ip = row.get("ADMIN_IP", "")
            cmd = remote_command(
                host, row,
                PXEBOOT_COMMANDS["minimal_os_ip_addr"],
            )
            key = row["HOSTNAME"]
            node_ips = _parse_ip_addresses(cmd.stdout)
            if expected_ip and expected_ip in node_ips:
                outcomes[key] = (True, f"admin IP {expected_ip} configured")
            else:
                outcomes[key] = (
                    False,
                    f"admin IP {expected_ip} not found",
                )

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("OS nodes", len(rows))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Network identity issues: " + ", ".join(failed)
            if failed
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
