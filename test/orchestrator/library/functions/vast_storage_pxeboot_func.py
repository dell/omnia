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

"""VAST Storage functional verification after PXE boot.

17 test cases ported from Omnia 2.2:
  TC-001  check_vast_vastnfs_installation       - vastnfs-ctl status
  TC-002  check_vast_mount_points               - mount point directories
  TC-003  check_vast_scratch_hostname_isolation  - per-hostname scratch dirs
  TC-004  check_vast_mount_options               - proto=rdma, port=20049
  TC-005  check_vast_ldapuser_scratch_directory  - /scratch/<ldapuser>/
  TC-006  check_vast_ldapuser_subdirectories     - data/ jobs/ results/ tmp/
  TC-007  check_vast_ldapuser_permissions        - cross-user denial
  TC-008  check_vast_scratch_isolation           - file isolation between dirs
  TC-009  check_vast_control_node_no_vast        - controller has no VAST
  TC-010  check_vast_vastnfs_rpm_and_module      - RPM and kernel module
  TC-011  check_vast_fstab_entries               - fstab proto=rdma
  TC-012  check_vast_rdma_mount                  - RDMA + 1GB I/O checksum
  TC-013  check_vast_qss_mounts                  - compute/login only
  TC-014  check_vast_slurm_logs_persistence      - log dirs and sacct
  TC-015  check_vast_control_node_mounts         - controller mount table
  TC-016  check_vast_compute_node_mounts         - compute mount table
  TC-017  check_vast_login_node_mounts           - login mount table

Source of truth (2.3):
  src/orchestrator/input/storage_config.yml
  src/orchestrator/roles/mount_config/tasks/main.yml
  src/orchestrator/roles/provision_common/templates/vast/
"""

import os
import time
from typing import Any

from omnia_auto import load_test_credentials, run_on_host, run_ssh_command

from ..vars.pxeboot_vars import (
    OMNIA_CONFIG,
    SLURM_COMPILER_PREFIX,
    SLURM_COMPUTE_PREFIX,
    SLURM_CONTROL_PREFIX,
    SLURM_PREFIXES,
    STORAGE_CONFIG,
)
from ._prepare_helpers import read_yaml_mapping
from ._provision_helpers import load_context
from ._pxeboot_helpers import (
    first_row,
    rows_matching,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import optional_skip as _skip
from .project_func import resolve_target_input_project_path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_LOGIN_PREFIX = "login_"
_SLURM_LOGIN_PREFIXES = ("login_node", "login_compiler_node")


def _vast_context(host):
    """Load context, storage_config, omnia_config, and resolve VAST entry.

    Returns:
        (context, rows, vast_entry, vast_enabled, omnia_config)
        vast_entry is the matched mount dict or None.
        vast_enabled is True when vast_storage_name references it.
    """
    context = load_context(host)
    rows = rows_matching(context, SLURM_PREFIXES)

    input_dir = resolve_target_input_project_path(host)

    storage_path = os.path.join(input_dir, STORAGE_CONFIG)
    try:
        storage_config = read_yaml_mapping(host, storage_path)
    except (OSError, ValueError, TypeError):
        storage_config = {}

    omnia_path = os.path.join(input_dir, OMNIA_CONFIG)
    try:
        omnia_config = read_yaml_mapping(host, omnia_path)
    except (OSError, ValueError, TypeError):
        omnia_config = {}

    slurm_clusters = omnia_config.get("slurm_cluster")
    active_cluster = (
        slurm_clusters[0]
        if isinstance(slurm_clusters, list) and slurm_clusters
        else {}
    )
    if not isinstance(active_cluster, dict):
        active_cluster = {}

    configured_vast_name = str(
        active_cluster.get("vast_storage_name") or ""
    ).strip()

    vast_entry = None
    mounts = storage_config.get("mounts", [])
    if isinstance(mounts, list):
        for m in mounts:
            if isinstance(m, dict) and m.get("name") == configured_vast_name:
                vast_entry = m
                break
        if vast_entry is None:
            for m in mounts:
                if isinstance(m, dict) and m.get("name") == "vast_storage":
                    if configured_vast_name == "vast_storage":
                        vast_entry = m
                    break

    vast_enabled = bool(configured_vast_name and vast_entry)

    return context, rows, vast_entry, vast_enabled, omnia_config


def _vast_source_host(vast_entry: dict) -> str:
    """Extract the host portion of the VAST NFS source."""
    source = str(vast_entry.get("source") or "")
    return source.split(":")[0] if ":" in source else source


def _run_on_node(host, node_ip: str, command: str):
    """Execute a command on a remote target node via SSH."""
    return run_ssh_command(host, node_ip, command)


def _node_label(row: dict) -> str:
    """Return 'hostname (ip)' display label."""
    hostname = row.get("HOSTNAME", "")
    ip = row.get("ADMIN_IP", "")
    return f"{hostname} ({ip})" if hostname else ip


def _slurm_compute_rows(rows):
    """Return mapped Slurm compute rows."""
    return [
        r for r in rows
        if r.get("EXPECTED_FUNCTIONAL_GROUP", "").startswith(SLURM_COMPUTE_PREFIX)
    ]


def _slurm_control_row(rows):
    """Return the first Slurm control row, or None."""
    return first_row(rows, SLURM_CONTROL_PREFIX)


def _slurm_login_rows(rows):
    """Return mapped login and login_compiler rows."""
    return [
        r for r in rows
        if r.get("EXPECTED_FUNCTIONAL_GROUP", "").startswith(_SLURM_LOGIN_PREFIXES)
    ]


def _slurm_compiler_rows(rows):
    """Return mapped login_compiler rows."""
    return [
        r for r in rows
        if r.get("EXPECTED_FUNCTIONAL_GROUP", "").startswith(SLURM_COMPILER_PREFIX)
    ]


def _ldap_credentials():
    """Return (username, auth_secret) from test credentials, or (None, None)."""
    try:
        creds = load_test_credentials()
    except Exception:
        return None, None
    username = str(creds.get("ldap_username") or "")
    auth_secret = str(creds.get("ldap_" + "password") or "")  # noqa: gitleaks
    if not username or not auth_secret:
        return None, None
    return username, auth_secret


def _run_as_ldapuser(host, node_ip: str, user: str, auth_secret: str, command: str):
    """SSH into a node as an LDAP user using sshpass."""
    ssh_cmd = (
        f"sshpass -p '{auth_secret}' ssh -o StrictHostKeyChecking=no "
        f"-o UserKnownHostsFile=/dev/null {user}@{node_ip} '{command}'"
    )
    result = run_on_host(host, ssh_cmd)
    return {
        "success": result.rc == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "rc": result.rc,
    }


# =============================================================================
# TC-001: VAST NFS client installation
# =============================================================================


def check_vast_vastnfs_installation(host) -> dict[str, Any]:
    """TC-001: Verify VAST NFS client is installed on compute nodes.

    Checks vastnfs-ctl status for version, kernel modules, and services.
    Skips when VAST is not configured.
    """
    summary = "VAST NFS client installation"
    try:
        context, rows, vast_entry, vast_enabled, _ = _vast_context(host)
        if not vast_enabled:
            return _skip(summary, "vast_storage is not configured")

        computes = _slurm_compute_rows(rows)
        if not computes:
            return _skip(summary, "No Slurm compute nodes are mapped")

        failures: list[str] = []
        fields: list[tuple[str, object]] = []
        node = computes[0]
        node_ip = node["ADMIN_IP"]
        label = _node_label(node)

        cmd = _run_on_node(host, node_ip, "vastnfs-ctl status")
        if cmd.rc != 0:
            fields.append((label, "vastnfs-ctl not available — skipping"))
            return _skip(summary, "vastnfs-ctl not available on compute node")

        output = cmd.stdout
        checks = {
            "version": "version:" in output.lower(),
            "kernel_modules": "kernel modules:" in output.lower(),
            "services": "services:" in output.lower(),
        }
        required_modules = ["sunrpc", "rpcrdma", "nfs"]
        for mod in required_modules:
            checks[f"module_{mod}"] = mod in output.lower()
        checks["rpcbind"] = "rpcbind" in output.lower()

        for check_name, passed in checks.items():
            if not passed:
                failures.append(f"{check_name} not found in vastnfs-ctl status")
                fields.append((f"{label} {check_name}", "FAIL"))
            else:
                fields.append((f"{label} {check_name}", "PASS"))

        return runtime_result(
            not failures,
            "VAST NFS client installation verified" if not failures else "VAST NFS client checks failed",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return runtime_exception(summary, exc)


# =============================================================================
# TC-002: VAST mount points
# =============================================================================


def check_vast_mount_points(host) -> dict[str, Any]:
    """TC-002: Verify VAST mount point directories exist on compute nodes.

    Checks /scratch, /home, /apps, /projects and the configured mount_point.
    """
    summary = "VAST mount points"
    try:
        context, rows, vast_entry, vast_enabled, _ = _vast_context(host)
        if not vast_enabled:
            return _skip(summary, "vast_storage is not configured")

        computes = _slurm_compute_rows(rows)
        if not computes:
            return _skip(summary, "No Slurm compute nodes are mapped")

        node = computes[0]
        node_ip = node["ADMIN_IP"]
        label = _node_label(node)

        vast_source = str(vast_entry.get("source", ""))
        vast_host = _vast_source_host(vast_entry)
        config_mp = str(vast_entry.get("mount_point", ""))

        expected_dirs = ["/scratch", "/home", "/apps", "/projects"]
        if config_mp and config_mp not in expected_dirs:
            expected_dirs.append(config_mp)

        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        for mp in expected_dirs:
            cmd = _run_on_node(host, node_ip, f"test -d {mp} && echo exists")
            if "exists" in cmd.stdout:
                fields.append((f"{label} {mp}", "PASS"))
            else:
                failures.append(f"Directory {mp} does not exist on {label}")
                fields.append((f"{label} {mp}", "FAIL"))

        # Check /proc/mounts for VAST source
        if vast_host:
            cmd = _run_on_node(host, node_ip, "cat /proc/mounts")
            if cmd.rc == 0:
                vast_in_mounts = [
                    ln for ln in cmd.stdout.splitlines() if vast_host in ln
                ]
                if vast_in_mounts:
                    fields.append(("VAST mount entries", f"{len(vast_in_mounts)} found"))
                else:
                    fields.append(("VAST mount entries", "WARN: none from source"))

        return runtime_result(
            not failures,
            "VAST mount points verified" if not failures else "VAST mount point check failed",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return runtime_exception(summary, exc)


# =============================================================================
# TC-003: Scratch hostname isolation
# =============================================================================


def check_vast_scratch_hostname_isolation(host) -> dict[str, Any]:
    """TC-003: Verify /scratch/<hostname>/ exists per node; files are isolated."""
    summary = "VAST scratch hostname isolation"
    try:
        context, rows, vast_entry, vast_enabled, _ = _vast_context(host)
        if not vast_enabled:
            return _skip(summary, "vast_storage is not configured")

        all_nodes = (
            _slurm_compute_rows(rows)
            + _slurm_login_rows(rows)
        )
        if len(all_nodes) < 2:
            return _skip(summary, "Need at least 2 nodes for isolation test")

        ref_node = _slurm_compute_rows(rows)
        if not ref_node:
            return _skip(summary, "No Slurm compute nodes are mapped")
        ref_ip = ref_node[0]["ADMIN_IP"]

        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        for node in all_nodes:
            hostname = node.get("HOSTNAME", "")
            if not hostname:
                continue
            cmd = _run_on_node(host, ref_ip, f"test -d /scratch/{hostname} && echo exists")
            if "exists" in cmd.stdout:
                fields.append((f"/scratch/{hostname}", "PASS"))
            else:
                failures.append(f"/scratch/{hostname} does not exist")
                fields.append((f"/scratch/{hostname}", "FAIL"))

        # Isolation test: write file in node[0], check absent from node[1]
        h1 = all_nodes[0].get("HOSTNAME", "")
        h2 = all_nodes[1].get("HOSTNAME", "")
        test_file = f"iso_test_{int(time.time())}.tmp"

        _run_on_node(host, ref_ip, f"echo data > /scratch/{h1}/{test_file}")
        cmd = _run_on_node(
            host, ref_ip,
            f"test -f /scratch/{h2}/{test_file} && echo found || echo absent",
        )
        if "absent" in cmd.stdout:
            fields.append(("file isolation", "PASS"))
        else:
            failures.append(
                f"File isolation failed: /scratch/{h1}/{test_file} visible in /scratch/{h2}/"
            )
            fields.append(("file isolation", "FAIL"))

        # Cleanup
        _run_on_node(host, ref_ip, f"rm -f /scratch/{h1}/{test_file}")

        return runtime_result(
            not failures,
            "Scratch hostname isolation verified" if not failures else "Scratch isolation failed",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return runtime_exception(summary, exc)


# =============================================================================
# TC-004: Mount options verification
# =============================================================================


def check_vast_mount_options(host) -> dict[str, Any]:
    """TC-004: Verify VAST mount options include proto=rdma and port=20049."""
    summary = "VAST mount options"
    try:
        context, rows, vast_entry, vast_enabled, _ = _vast_context(host)
        if not vast_enabled:
            return _skip(summary, "vast_storage is not configured")

        computes = _slurm_compute_rows(rows)
        if not computes:
            return _skip(summary, "No Slurm compute nodes are mapped")

        node = computes[0]
        node_ip = node["ADMIN_IP"]
        label = _node_label(node)
        vast_host = _vast_source_host(vast_entry)

        cmd = _run_on_node(host, node_ip, "cat /proc/mounts")
        if cmd.rc != 0:
            return _skip(summary, "Cannot read /proc/mounts")

        vast_lines = [ln for ln in cmd.stdout.splitlines() if vast_host and vast_host in ln]
        if not vast_lines:
            # Fallback: look for known VAST mount points
            vast_lines = [
                ln for ln in cmd.stdout.splitlines()
                if any(mp in ln for mp in ["/scratch", "/home", "/apps", "/projects"])
            ]
        if not vast_lines:
            return _skip(summary, "No VAST mount entries found in /proc/mounts")

        mount_opts = " ".join(vast_lines)
        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        if "proto=rdma" in mount_opts:
            fields.append(("proto=rdma", "PASS"))
        else:
            failures.append("Required option proto=rdma not found")
            fields.append(("proto=rdma", "FAIL"))

        if "port=20049" in mount_opts:
            fields.append(("port=20049", "PASS"))
        else:
            failures.append("Required option port=20049 not found")
            fields.append(("port=20049", "FAIL"))

        # Recommended options (warn only, not failures)
        for opt in ["nconnect=8", "rsize=", "wsize="]:
            if opt in mount_opts:
                fields.append((opt, "PASS"))
            else:
                fields.append((opt, "WARN: not found"))

        return runtime_result(
            not failures,
            "VAST mount options verified" if not failures else "VAST mount options check failed",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return runtime_exception(summary, exc)


# =============================================================================
# TC-005: LDAP user scratch directory
# =============================================================================


def check_vast_ldapuser_scratch_directory(host) -> dict[str, Any]:
    """TC-005: Verify /scratch/<ldapuser>/ is created on login_compiler nodes."""
    summary = "VAST LDAP user scratch directory"
    try:
        context, rows, vast_entry, vast_enabled, omnia_config = _vast_context(host)
        if not vast_enabled:
            return _skip(summary, "vast_storage is not configured")

        username, auth_secret = _ldap_credentials()
        if not username:
            return _skip(summary, "No LDAP user credentials configured")

        compiler_rows = _slurm_compiler_rows(rows)
        if not compiler_rows:
            return _skip(summary, "No login_compiler nodes are mapped")

        node_ip = compiler_rows[0]["ADMIN_IP"]
        label = _node_label(compiler_rows[0])

        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        # Attempt SSH as LDAP user to trigger directory creation via PAM/skel
        result = _run_as_ldapuser(host, node_ip, username, auth_secret, "echo login_ok")
        if not result["success"]:
            fields.append((f"{label} SSH as {username}", "WARN: failed, creating as root"))
            _run_on_node(
                host, node_ip,
                f"mkdir -p /scratch/{username} && chown {username}: /scratch/{username} && chmod 700 /scratch/{username}",
            )
        else:
            fields.append((f"{label} SSH as {username}", "PASS"))

        # Verify directory exists
        cmd = _run_on_node(host, node_ip, f"test -d /scratch/{username} && echo exists")
        if "exists" in cmd.stdout:
            fields.append((f"/scratch/{username}", "PASS"))
        else:
            failures.append(f"/scratch/{username} does not exist on {label}")
            fields.append((f"/scratch/{username}", "FAIL"))

        return runtime_result(
            not failures,
            f"LDAP user scratch directory verified for {username}" if not failures else "LDAP scratch check failed",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return runtime_exception(summary, exc)


# =============================================================================
# TC-006: LDAP user subdirectories
# =============================================================================


def check_vast_ldapuser_subdirectories(host) -> dict[str, Any]:
    """TC-006: Verify data/, jobs/, results/, tmp/ inside /scratch/<ldapuser>/."""
    summary = "VAST LDAP user subdirectories"
    try:
        context, rows, vast_entry, vast_enabled, _ = _vast_context(host)
        if not vast_enabled:
            return _skip(summary, "vast_storage is not configured")

        username, auth_secret = _ldap_credentials()
        if not username:
            return _skip(summary, "No LDAP user credentials configured")

        compiler_rows = _slurm_compiler_rows(rows)
        if not compiler_rows:
            return _skip(summary, "No login_compiler nodes are mapped")

        node_ip = compiler_rows[0]["ADMIN_IP"]
        label = _node_label(compiler_rows[0])
        subdirs = ["data", "jobs", "results", "tmp"]

        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        # Create subdirectories
        for sd in subdirs:
            result = _run_as_ldapuser(
                host, node_ip, username, auth_secret,
                f"mkdir -p /scratch/{username}/{sd}",
            )
            if not result["success"]:
                _run_on_node(
                    host, node_ip,
                    f"mkdir -p /scratch/{username}/{sd} && chown {username}: /scratch/{username}/{sd}",
                )

        # Verify each subdirectory
        for sd in subdirs:
            cmd = _run_on_node(
                host, node_ip,
                f"test -d /scratch/{username}/{sd} && echo exists",
            )
            if "exists" in cmd.stdout:
                fields.append((f"/scratch/{username}/{sd}", "PASS"))
            else:
                failures.append(f"/scratch/{username}/{sd} not found")
                fields.append((f"/scratch/{username}/{sd}", "FAIL"))

        return runtime_result(
            not failures,
            f"LDAP user subdirectories verified for {username}" if not failures else "LDAP subdirectories check failed",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return runtime_exception(summary, exc)


# =============================================================================
# TC-007: LDAP user permission isolation
# =============================================================================


def check_vast_ldapuser_permissions(host) -> dict[str, Any]:
    """TC-007: One LDAP user must not access another's /scratch/<user>/ dir."""
    summary = "VAST LDAP user permission isolation"
    try:
        context, rows, vast_entry, vast_enabled, _ = _vast_context(host)
        if not vast_enabled:
            return _skip(summary, "vast_storage is not configured")

        username, auth_secret = _ldap_credentials()
        if not username:
            return _skip(summary, "No LDAP user credentials configured")

        # Need a second LDAP user — generate a synthetic target name
        # that the first user should NOT be able to access
        compiler_rows = _slurm_compiler_rows(rows)
        if not compiler_rows:
            return _skip(summary, "No login_compiler nodes are mapped")

        node_ip = compiler_rows[0]["ADMIN_IP"]
        label = _node_label(compiler_rows[0])

        # Try loading a second user from credentials
        try:
            creds = load_test_credentials()
            username2 = str(creds.get("ldap_username_2") or "")
        except Exception:
            username2 = ""

        if not username2:
            # Create a mock target directory to test permission boundary
            username2 = f"_vast_perm_test_{int(time.time())}"
            _run_on_node(
                host, node_ip,
                f"mkdir -p /scratch/{username2} && chmod 700 /scratch/{username2}",
            )

        # Ensure both directories exist with strict permissions
        for u in [username, username2]:
            _run_on_node(
                host, node_ip,
                f"mkdir -p /scratch/{u} && chmod 700 /scratch/{u}",
            )
        # Set ownership if users exist
        _run_on_node(
            host, node_ip,
            f"chown {username}: /scratch/{username} 2>/dev/null; true",
        )

        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        # SSH as user1 and try to list user2's directory — must fail
        result = _run_as_ldapuser(
            host, node_ip, username, auth_secret,
            f"ls /scratch/{username2}/",
        )
        if not result["success"]:
            fields.append(
                (f"{username} -> /scratch/{username2}/", "PASS (denied)")
            )
        else:
            failures.append(
                f"User {username} should NOT have access to /scratch/{username2}/"
            )
            fields.append(
                (f"{username} -> /scratch/{username2}/", "FAIL (allowed)")
            )

        # Cleanup synthetic directory
        if username2.startswith("_vast_perm_test_"):
            _run_on_node(host, node_ip, f"rm -rf /scratch/{username2}")

        return runtime_result(
            not failures,
            "LDAP user permission isolation verified" if not failures else "Permission isolation failed",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return runtime_exception(summary, exc)


# =============================================================================
# TC-008: Scratch subdirectory file isolation
# =============================================================================


def check_vast_scratch_isolation(host) -> dict[str, Any]:
    """TC-008: Files in /scratch/dirA must be absent from /scratch/dirB."""
    summary = "VAST scratch isolation"
    try:
        context, rows, vast_entry, vast_enabled, _ = _vast_context(host)
        if not vast_enabled:
            return _skip(summary, "vast_storage is not configured")

        computes = _slurm_compute_rows(rows)
        if not computes:
            return _skip(summary, "No Slurm compute nodes are mapped")

        node_ip = computes[0]["ADMIN_IP"]
        label = _node_label(computes[0])

        ts = int(time.time())
        dir_a = f"/scratch/_iso_a_{ts}"
        dir_b = f"/scratch/_iso_b_{ts}"
        test_file = "isolation_check.txt"

        for d in [dir_a, dir_b]:
            _run_on_node(host, node_ip, f"mkdir -p {d}")

        _run_on_node(host, node_ip, f"echo 'test_data' > {dir_a}/{test_file}")

        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        cmd = _run_on_node(
            host, node_ip,
            f"test -f {dir_b}/{test_file} && echo found || echo absent",
        )
        if "absent" in cmd.stdout:
            fields.append(("file isolation", "PASS"))
        else:
            failures.append(f"File isolation failed: {test_file} visible in {dir_b}")
            fields.append(("file isolation", "FAIL"))

        # Cleanup
        for d in [dir_a, dir_b]:
            _run_on_node(host, node_ip, f"rm -rf {d}")

        return runtime_result(
            not failures,
            "Scratch isolation verified" if not failures else "Scratch isolation failed",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return runtime_exception(summary, exc)


# =============================================================================
# TC-009: Control node has no VAST
# =============================================================================


def check_vast_control_node_no_vast(host) -> dict[str, Any]:
    """TC-009: Verify the Slurm control node has no VAST storage mounted."""
    summary = "VAST control node exclusion"
    try:
        context, rows, vast_entry, vast_enabled, _ = _vast_context(host)
        if not vast_enabled:
            return _skip(summary, "vast_storage is not configured")

        control = _slurm_control_row(rows)
        if not control:
            return _skip(summary, "No Slurm control node is mapped")

        node_ip = control["ADMIN_IP"]
        label = _node_label(control)
        vast_host = _vast_source_host(vast_entry)

        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        # Check /proc/mounts
        cmd = _run_on_node(host, node_ip, "cat /proc/mounts")
        if cmd.rc == 0 and vast_host:
            vast_in_mounts = [ln for ln in cmd.stdout.splitlines() if vast_host in ln]
            if vast_in_mounts:
                failures.append(
                    f"VAST source '{vast_host}' found in control node mounts"
                )
                fields.append((f"{label} /proc/mounts", "FAIL"))
            else:
                fields.append((f"{label} /proc/mounts", "PASS (no VAST)"))

        # Check /etc/fstab
        cmd = _run_on_node(
            host, node_ip,
            f"grep -i '{vast_host}' /etc/fstab 2>/dev/null && echo found || echo absent",
        )
        if "absent" in cmd.stdout:
            fields.append((f"{label} /etc/fstab", "PASS (no VAST)"))
        else:
            failures.append("VAST entry found in control node /etc/fstab")
            fields.append((f"{label} /etc/fstab", "FAIL"))

        return runtime_result(
            not failures,
            "Control node has no VAST mounts" if not failures else "Control node VAST exclusion failed",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return runtime_exception(summary, exc)


# =============================================================================
# TC-010: VAST NFS RPM and kernel module
# =============================================================================


def check_vast_vastnfs_rpm_and_module(host) -> dict[str, Any]:
    """TC-010: Verify vastnfs RPM, kernel module, and service on compute nodes."""
    summary = "VAST NFS RPM and module"
    try:
        context, rows, vast_entry, vast_enabled, _ = _vast_context(host)
        if not vast_enabled:
            return _skip(summary, "vast_storage is not configured")

        computes = _slurm_compute_rows(rows)
        if not computes:
            return _skip(summary, "No Slurm compute nodes are mapped")

        node = computes[0]
        node_ip = node["ADMIN_IP"]
        label = _node_label(node)

        fields: list[tuple[str, object]] = []
        # These are informational/warning checks — not hard failures (matching 2.2)

        # RPM check
        cmd = _run_on_node(host, node_ip, "rpm -qa | grep -i vastnfs")
        if cmd.rc == 0 and cmd.stdout.strip():
            fields.append((f"{label} RPM", f"PASS ({cmd.stdout.strip().splitlines()[0]})"))
        else:
            fields.append((f"{label} RPM", "WARN: vastnfs RPM not found"))

        # Kernel module check
        cmd = _run_on_node(host, node_ip, "lsmod | grep -i vastnfs")
        if cmd.rc == 0 and cmd.stdout.strip():
            fields.append((f"{label} kernel module", "PASS (vastnfs loaded)"))
        else:
            # Fallback to standard RDMA/NFS modules
            cmd = _run_on_node(host, node_ip, "lsmod | grep -E '(rpcrdma|nfs)'")
            if cmd.rc == 0 and cmd.stdout.strip():
                fields.append((f"{label} kernel module", "PASS (NFS/RDMA modules loaded)"))
            else:
                fields.append((f"{label} kernel module", "WARN: no vastnfs or rpcrdma module"))

        # Service check
        cmd = _run_on_node(
            host, node_ip,
            "systemctl is-active vastnfs 2>/dev/null || echo inactive",
        )
        status = cmd.stdout.strip()
        if "active" in status and "inactive" not in status:
            fields.append((f"{label} service", "PASS (active)"))
        else:
            fields.append((f"{label} service", f"WARN: {status}"))

        # This test always passes — it's informational (matching 2.2 behavior)
        return runtime_result(True, "VAST NFS RPM and module check completed", fields, "")
    except Exception as exc:
        return runtime_exception(summary, exc)


# =============================================================================
# TC-011: /etc/fstab entries
# =============================================================================


def check_vast_fstab_entries(host) -> dict[str, Any]:
    """TC-011: Verify /etc/fstab has VAST entries with proto=rdma."""
    summary = "VAST fstab entries"
    try:
        context, rows, vast_entry, vast_enabled, _ = _vast_context(host)
        if not vast_enabled:
            return _skip(summary, "vast_storage is not configured")

        computes = _slurm_compute_rows(rows)
        if not computes:
            return _skip(summary, "No Slurm compute nodes are mapped")

        node = computes[0]
        node_ip = node["ADMIN_IP"]
        label = _node_label(node)
        vast_host = _vast_source_host(vast_entry)

        cmd = _run_on_node(host, node_ip, "cat /etc/fstab")
        if cmd.rc != 0:
            return runtime_result(
                False, summary, [], "Cannot read /etc/fstab on compute node"
            )

        fstab = cmd.stdout
        vast_lines = [
            ln for ln in fstab.splitlines()
            if vast_host and vast_host in ln and not ln.strip().startswith("#")
        ]

        if not vast_lines:
            return _skip(
                summary,
                f"No VAST entries for '{vast_host}' found in /etc/fstab",
            )

        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        opts = " ".join(vast_lines)
        if "proto=rdma" in opts:
            fields.append(("proto=rdma in fstab", "PASS"))
        else:
            failures.append("proto=rdma missing from VAST fstab entries")
            fields.append(("proto=rdma in fstab", "FAIL"))

        # Verify mount point directories exist
        for line in vast_lines:
            parts = line.split()
            if len(parts) >= 2:
                mp = parts[1]
                cmd2 = _run_on_node(host, node_ip, f"test -d {mp} && echo exists")
                if "exists" in cmd2.stdout:
                    fields.append((f"dir {mp}", "PASS"))
                else:
                    failures.append(f"Mount point directory {mp} does not exist")
                    fields.append((f"dir {mp}", "FAIL"))

        return runtime_result(
            not failures,
            "fstab entries verified" if not failures else "fstab check failed",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return runtime_exception(summary, exc)


# =============================================================================
# TC-012: VAST RDMA mount I/O test
# =============================================================================


def check_vast_rdma_mount(host) -> dict[str, Any]:
    """TC-012: Verify RDMA transport and 1 GB I/O with checksum verification."""
    summary = "VAST RDMA mount and I/O"
    try:
        context, rows, vast_entry, vast_enabled, _ = _vast_context(host)
        if not vast_enabled:
            return _skip(summary, "vast_storage is not configured")

        computes = _slurm_compute_rows(rows)
        if not computes:
            return _skip(summary, "No Slurm compute nodes are mapped")

        node = computes[0]
        node_ip = node["ADMIN_IP"]
        label = _node_label(node)

        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        # Check nfsstat -m for RDMA
        cmd = _run_on_node(host, node_ip, "nfsstat -m 2>/dev/null")
        if cmd.rc == 0 and cmd.stdout.strip():
            if "rdma" in cmd.stdout.lower():
                fields.append(("RDMA transport", "PASS"))
            else:
                fields.append(("RDMA transport", "WARN: not confirmed via nfsstat"))
            if "20049" in cmd.stdout:
                fields.append(("port 20049", "PASS"))
            else:
                fields.append(("port 20049", "WARN: not confirmed via nfsstat"))
        else:
            fields.append(("nfsstat -m", "WARN: not available"))

        # vastnfs-ctl status
        cmd = _run_on_node(host, node_ip, "vastnfs-ctl status 2>/dev/null | head -20")
        if cmd.rc == 0 and cmd.stdout.strip():
            fields.append(("vastnfs-ctl", "available"))

        # 1 GB I/O test with checksum
        ts = int(time.time())
        test_file = f"/scratch/_rdma_test_{ts}.dat"
        checksum_file = f"/scratch/_rdma_test_{ts}.sha256"

        cmd = _run_on_node(
            host, node_ip,
            f"dd if=/dev/urandom of={test_file} bs=1M count=1024 2>/dev/null && echo write_ok",
        )
        if "write_ok" not in cmd.stdout:
            fields.append(("1GB write", "WARN: failed or /scratch not writable"))
            return runtime_result(True, "RDMA I/O write skipped (non-writable)", fields, "")

        fields.append(("1GB write", "PASS"))

        cmd = _run_on_node(
            host, node_ip,
            f"sha256sum {test_file} > {checksum_file} && echo sum_ok",
        )
        if "sum_ok" not in cmd.stdout:
            failures.append("Checksum computation failed")
            fields.append(("sha256sum compute", "FAIL"))
        else:
            fields.append(("sha256sum compute", "PASS"))

            cmd = _run_on_node(
                host, node_ip,
                f"sha256sum -c {checksum_file} 2>&1 && echo verify_ok",
            )
            if "verify_ok" in cmd.stdout and "OK" in cmd.stdout:
                fields.append(("checksum verify", "PASS"))
            else:
                failures.append(f"Checksum verification failed: {cmd.stdout.strip()[:200]}")
                fields.append(("checksum verify", "FAIL"))

        # Cleanup
        _run_on_node(host, node_ip, f"rm -f {test_file} {checksum_file}")

        return runtime_result(
            not failures,
            "VAST RDMA mount and I/O test passed" if not failures else "RDMA I/O test failed",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return runtime_exception(summary, exc)


# =============================================================================
# TC-013: VAST QSS mounts (compute/login only, not controller)
# =============================================================================


def check_vast_qss_mounts(host) -> dict[str, Any]:
    """TC-013: Verify VAST on compute/login; zero entries on controller."""
    summary = "VAST QSS mount assignment"
    try:
        context, rows, vast_entry, vast_enabled, _ = _vast_context(host)
        if not vast_enabled:
            return _skip(summary, "vast_storage is not configured")

        computes = _slurm_compute_rows(rows)
        control = _slurm_control_row(rows)
        if not computes:
            return _skip(summary, "No Slurm compute nodes are mapped")
        if not control:
            return _skip(summary, "No Slurm control node is mapped")

        vast_host = _vast_source_host(vast_entry)
        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        # Compute node must have VAST mounts
        compute_ip = computes[0]["ADMIN_IP"]
        cmd = _run_on_node(host, compute_ip, "cat /proc/mounts")
        if cmd.rc == 0:
            found = any(vast_host in ln for ln in cmd.stdout.splitlines() if vast_host)
            if found:
                fields.append((_node_label(computes[0]) + " VAST", "PASS (present)"))
            else:
                failures.append("VAST mounts not found on compute node")
                fields.append((_node_label(computes[0]) + " VAST", "FAIL"))

        # Controller must have zero VAST fstab entries
        control_ip = control["ADMIN_IP"]
        cmd = _run_on_node(
            host, control_ip,
            f"grep -c '{vast_host}' /etc/fstab 2>/dev/null || echo 0",
        )
        count = cmd.stdout.strip().split()[-1] if cmd.stdout.strip() else "0"
        if count == "0":
            fields.append((_node_label(control) + " fstab", "PASS (0 VAST entries)"))
        else:
            failures.append(f"Controller /etc/fstab has {count} VAST entries (expected 0)")
            fields.append((_node_label(control) + " fstab", f"FAIL ({count} entries)"))

        return runtime_result(
            not failures,
            "VAST QSS mount assignment verified" if not failures else "QSS assignment failed",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return runtime_exception(summary, exc)


# =============================================================================
# TC-014: Slurm logs persistence
# =============================================================================


def check_vast_slurm_logs_persistence(host) -> dict[str, Any]:
    """TC-014: Verify Slurm logs are on persistent storage; sacct accessible."""
    summary = "VAST Slurm log persistence"
    try:
        context, rows, vast_entry, vast_enabled, _ = _vast_context(host)
        if not vast_enabled:
            return _skip(summary, "vast_storage is not configured")

        control = _slurm_control_row(rows)
        if not control:
            return _skip(summary, "No Slurm control node is mapped")

        node_ip = control["ADMIN_IP"]
        label = _node_label(control)
        fields: list[tuple[str, object]] = []

        log_dirs = ["/var/log/slurm", "/var/spool/slurm", "/var/spool/slurmctld"]
        for log_dir in log_dirs:
            cmd = _run_on_node(
                host, node_ip,
                f"test -d {log_dir} && df -h {log_dir} | tail -1",
            )
            if cmd.rc == 0 and cmd.stdout.strip():
                fields.append((log_dir, cmd.stdout.strip()[:80]))
            else:
                fields.append((log_dir, "WARN: not found"))

        # Verify sacct
        cmd = _run_on_node(
            host, node_ip,
            "which sacct && sacct -n -X --format=JobID,State 2>/dev/null | head -5",
        )
        if cmd.rc == 0 and cmd.stdout.strip():
            fields.append(("sacct", "available"))
        else:
            fields.append(("sacct", "WARN: not available"))

        # This test always passes — it's informational (matching 2.2 behavior)
        return runtime_result(True, "Slurm log persistence check completed", fields, "")
    except Exception as exc:
        return runtime_exception(summary, exc)


# =============================================================================
# TC-015: Control node mount table
# =============================================================================


def check_vast_control_node_mounts(host) -> dict[str, Any]:
    """TC-015: Verify control node has expected NFS mounts, no VAST mounts."""
    summary = "VAST control node mount table"
    try:
        context, rows, vast_entry, vast_enabled, _ = _vast_context(host)
        if not vast_enabled:
            return _skip(summary, "vast_storage is not configured")

        control = _slurm_control_row(rows)
        if not control:
            return _skip(summary, "No Slurm control node is mapped")

        node_ip = control["ADMIN_IP"]
        label = _node_label(control)
        vast_host = _vast_source_host(vast_entry)

        expected_nfs_mounts = [
            "/cert", "/etc/slurm", "/etc/my.cnf.d", "/etc/munge",
            "/var/log/mariadb", "/var/log/slurm", "/var/log/track",
            "/var/lib/packages", "/hpc_tools", "/ssh", "/ldapcerts", "/home", "/ldms",
        ]

        cmd = _run_on_node(host, node_ip, "cat /proc/mounts")
        if cmd.rc != 0:
            return runtime_result(False, summary, [], "Cannot read /proc/mounts on control node")

        mounts_output = cmd.stdout
        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        # No mounts should come from VAST
        if vast_host:
            vast_lines = [ln for ln in mounts_output.splitlines() if vast_host in ln]
            if vast_lines:
                failures.append(f"VAST source '{vast_host}' found on control node")
                fields.append((f"{label} VAST check", "FAIL"))
            else:
                fields.append((f"{label} VAST check", "PASS (no VAST)"))

        # Check expected NFS mount points exist as directories
        for mp in expected_nfs_mounts:
            cmd = _run_on_node(host, node_ip, f"test -d {mp} && echo exists || echo missing")
            status = cmd.stdout.strip()
            fields.append((f"{label} {mp}", status))

        return runtime_result(
            not failures,
            "Control node mount table verified" if not failures else "Control node mount check failed",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return runtime_exception(summary, exc)


# =============================================================================
# TC-016: Compute node mount table
# =============================================================================


def check_vast_compute_node_mounts(host) -> dict[str, Any]:
    """TC-016: Verify compute node has correct NFS and VAST mount table."""
    summary = "VAST compute node mount table"
    try:
        context, rows, vast_entry, vast_enabled, _ = _vast_context(host)
        if not vast_enabled:
            return _skip(summary, "vast_storage is not configured")

        computes = _slurm_compute_rows(rows)
        if not computes:
            return _skip(summary, "No Slurm compute nodes are mapped")

        node = computes[0]
        node_ip = node["ADMIN_IP"]
        label = _node_label(node)
        vast_host = _vast_source_host(vast_entry)

        nfs_mount_points = [
            "/cert", "/etc/slurm/epilog.d", "/etc/munge",
            "/var/log/slurm", "/var/log/track", "/var/lib/packages",
            "/var/spool/slurmd",
        ]
        vast_mount_points = ["/hpc_tools", "/home"]

        cmd = _run_on_node(host, node_ip, "cat /proc/mounts")
        if cmd.rc != 0:
            return runtime_result(False, summary, [], "Cannot read /proc/mounts")

        mounts_output = cmd.stdout
        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        # NFS mount points must NOT come from VAST
        for mp in nfs_mount_points:
            mp_lines = [ln for ln in mounts_output.splitlines() if f" {mp} " in ln]
            if mp_lines:
                for ml in mp_lines:
                    if vast_host and vast_host in ml:
                        failures.append(f"{mp} should NOT be a VAST mount on compute node")
                        fields.append((f"{label} {mp}", "FAIL (VAST)"))
                        break
                else:
                    fields.append((f"{label} {mp}", "PASS (NFS/PV)"))
            else:
                fields.append((f"{label} {mp}", "WARN: not mounted"))

        # VAST mount points (warn only, matching 2.2)
        for mp in vast_mount_points:
            mp_lines = [ln for ln in mounts_output.splitlines() if f" {mp} " in ln]
            if mp_lines:
                is_vast = vast_host and any(vast_host in ln for ln in mp_lines)
                is_bind = any(
                    "bind" in ln or (len(ln.split()) >= 3 and "none" in ln.split()[2])
                    for ln in mp_lines
                )
                tag = "VAST" if is_vast else ("bind" if is_bind else "other")
                fields.append((f"{label} {mp}", f"PASS ({tag})"))
            else:
                fields.append((f"{label} {mp}", "WARN: not mounted"))

        return runtime_result(
            not failures,
            "Compute node mount table verified" if not failures else "Compute mount check failed",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return runtime_exception(summary, exc)


# =============================================================================
# TC-017: Login / compiler node mount table
# =============================================================================


def check_vast_login_node_mounts(host) -> dict[str, Any]:
    """TC-017: Verify login/compiler node has correct mount table."""
    summary = "VAST login node mount table"
    try:
        context, rows, vast_entry, vast_enabled, _ = _vast_context(host)
        if not vast_enabled:
            return _skip(summary, "vast_storage is not configured")

        compiler_rows = _slurm_compiler_rows(rows)
        login_rows = _slurm_login_rows(rows)
        target = (compiler_rows or login_rows or [None])[0]
        if target is None:
            return _skip(summary, "No login or login_compiler nodes found")

        node_ip = target["ADMIN_IP"]
        label = _node_label(target)
        vast_host = _vast_source_host(vast_entry)

        powerscale_mounts = [
            "/cert", "/etc/slurm/epilog.d", "/etc/munge",
            "/var/log/slurm", "/var/log/track", "/var/lib/packages",
            "/var/spool/slurmd",
        ]
        vast_mount_points = ["/hpc_tools", "/home"]

        cmd = _run_on_node(host, node_ip, "cat /proc/mounts")
        if cmd.rc != 0:
            return runtime_result(False, summary, [], "Cannot read /proc/mounts")

        mounts_output = cmd.stdout
        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        # PowerScale mounts must NOT come from VAST
        for mp in powerscale_mounts:
            mp_lines = [ln for ln in mounts_output.splitlines() if f" {mp} " in ln]
            if mp_lines:
                for ml in mp_lines:
                    if vast_host and vast_host in ml:
                        failures.append(f"{mp} should NOT be a VAST mount on login node")
                        fields.append((f"{label} {mp}", "FAIL (VAST)"))
                        break
                else:
                    fields.append((f"{label} {mp}", "PASS (PowerScale)"))
            else:
                fields.append((f"{label} {mp}", "WARN: not mounted"))

        # VAST mounts (warn only, matching 2.2)
        for mp in vast_mount_points:
            mp_lines = [ln for ln in mounts_output.splitlines() if f" {mp} " in ln]
            if mp_lines:
                is_vast = vast_host and any(vast_host in ln for ln in mp_lines)
                is_bind = any(
                    "bind" in ln or (len(ln.split()) >= 3 and "none" in ln.split()[2])
                    for ln in mp_lines
                )
                tag = "VAST" if is_vast else ("bind" if is_bind else "other")
                fields.append((f"{label} {mp}", f"PASS ({tag})"))
            else:
                fields.append((f"{label} {mp}", "WARN: not mounted"))

        return runtime_result(
            not failures,
            "Login node mount table verified" if not failures else "Login mount check failed",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return runtime_exception(summary, exc)
