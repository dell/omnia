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

"""Private helpers for PowerVault iSCSI storage verification.

25 tests mapped from Omnia 2.2 to 2.3 source code:
- iSCSI infrastructure (6 tests)
- Multipath validation (3 tests)
- Partition/filesystem/mount (5 tests)
- Bind mount validation (4 tests)
- Functional group targeting (2 tests)
- Cloud-init validation (2 tests)
- Writability/duplicates (3 tests)

Excluded (not in 2.3 source):
- I/O tests (TC-PV-022, TC-PV-023)
- Slurm-specific tests (TC-PV-027, TC-PV-028)
"""

import posixpath
import re
from typing import Any

import yaml

from omnia_auto import run_on_host, run_ssh_command

from ..vars.pxeboot_vars import (
    POWERVAULT_DEFAULT_FS_TYPE,
    POWERVAULT_DEFAULT_ISCSI_PORT,
    POWERVAULT_DEFAULT_MOUNT_OPTS,
    POWERVAULT_DEFAULT_NODE_KEY,
    POWERVAULT_ISCSI_INITIATOR_PATH,
    POWERVAULT_LOG_COMPLETE_MSG,
    POWERVAULT_LOG_TEMPLATE,
    POWERVAULT_PORT_CHECK_TIMEOUT,
    PXEBOOT_COMMANDS,
)
from ._provision_helpers import load_context
from ._pxeboot_helpers import runtime_result
from .project_func import resolve_target_input_project_path


def optional_skip(summary: str, reason: str) -> dict[str, Any]:
    """Return the canonical skip result consumed by verify_pxeboot."""
    return runtime_result(True, summary, [("Reason", reason)], "", skipped=True)


def error_result(summary: str, error: str) -> dict[str, Any]:
    """Return a bounded failed result for a probe or exception."""
    return runtime_result(False, summary, [], error[:400])


def _run_on_node(host, node_ip: str, command: str):
    """Execute a command on a remote target node via SSH.

    Node-specific probes (iSCSI, multipath, mount, fstab, log, permissions)
    must run on the actual deployed node, not on the OIM.
    """
    return run_ssh_command(host, node_ip, command)


# =============================================================================
# CONFIGURATION READER FUNCTIONS
# =============================================================================


def read_storage_config(host) -> dict[str, Any]:
    """Read and parse storage_config.yml from the active 2.3 project.

    Resolves the storage path dynamically through the project framework
    so non-default projects are discovered correctly.

    Args:
        host: Testinfra host object

    Returns:
        Parsed storage_config dict, or empty dict when the file is absent
        (PowerVault not configured for this project).

    Raises:
        RuntimeError: When the file exists but cannot be read or parsed —
            an unreadable configured file is an error, not an absent feature.
    """
    input_dir = resolve_target_input_project_path(host)
    storage_path = posixpath.join(input_dir, "storage_config.yml")
    probe = run_on_host(host, f"test -f {storage_path} && echo exists || echo absent")
    if probe.stdout.strip() != "exists":
        return {}
    cmd = run_on_host(host, f"cat {storage_path}")
    if cmd.rc != 0:
        raise RuntimeError(
            f"storage_config.yml exists at {storage_path} but cannot be read "
            f"(rc={cmd.rc}): {cmd.stderr.strip()}"
        )
    try:
        return yaml.safe_load(cmd.stdout) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(
            f"storage_config.yml at {storage_path} contains invalid YAML: {exc}"
        ) from exc


def get_powervault_entries(host) -> list[dict[str, Any]]:
    """Extract powervault_config list from storage_config.yml.

    Args:
        host: Testinfra host object

    Returns:
        List of powervault_config entries, or empty list
    """
    config = read_storage_config(host)
    return config.get("powervault_config", []) or []


def get_mount_params(host) -> dict[str, Any]:
    """Extract mount_params section from storage_config.yml.

    Args:
        host: Testinfra host object

    Returns:
        Dict of mount_params profiles, or empty dict
    """
    config = read_storage_config(host)
    return config.get("mount_params", {}) or {}


def skip_if_no_powervault(host) -> bool:
    """Return True if powervault_config is absent or empty, indicating skip."""
    entries = get_powervault_entries(host)
    return len(entries) == 0


def resolve_pv_fs_type(pv_entry: dict, mount_params: dict) -> str:
    """Resolve the effective fs_type for a PV entry.

    Priority: pv_entry.fs_type > mount_params profile > default 'xfs'
    """
    if pv_entry.get("fs_type"):
        return pv_entry["fs_type"]
    profile_name = pv_entry.get("mount_params", "")
    if profile_name and profile_name in mount_params:
        return mount_params[profile_name].get("fs_type", POWERVAULT_DEFAULT_FS_TYPE)
    return POWERVAULT_DEFAULT_FS_TYPE


def resolve_pv_mount_opts(pv_entry: dict, mount_params: dict) -> str:
    """Resolve the effective mount options for a PV entry.

    Priority: pv_entry.mnt_opts > mount_params profile > default
    """
    if pv_entry.get("mnt_opts"):
        return pv_entry["mnt_opts"]
    profile_name = pv_entry.get("mount_params", "")
    if profile_name and profile_name in mount_params:
        return mount_params[profile_name].get("mnt_opts", POWERVAULT_DEFAULT_MOUNT_OPTS)
    return POWERVAULT_DEFAULT_MOUNT_OPTS


# =============================================================================
# NODE DISCOVERY FUNCTIONS
# =============================================================================


def _effective_group(row: dict) -> str:
    """Return the computed functional group for a PXE row.

    Uses ``EXPECTED_FUNCTIONAL_GROUP`` (the post-promotion value set by
    Ansible's ``determine_target_groups.yml``) and falls back to
    ``FUNCTIONAL_GROUP_NAME`` for rows that pre-date the promotion step.
    """
    return str(
        row.get("EXPECTED_FUNCTIONAL_GROUP")
        or row.get("FUNCTIONAL_GROUP_NAME")
        or ""
    )


def get_target_nodes(host, functional_group_prefix: list[str] | str) -> list[dict[str, str]]:
    """Return nodes matching any of the given functional_group_prefix values.

    Uses prefix matching against ``EXPECTED_FUNCTIONAL_GROUP`` (the
    post-promotion computed group) in the PXE mapping, mirroring the
    Ansible determine_target_groups.yml logic.

    Args:
        host: Testinfra host object
        functional_group_prefix: List of prefix strings or single string

    Returns:
        List of node info dicts with admin_ip, hostname, functional_group, etc.
    """
    if isinstance(functional_group_prefix, str):
        functional_group_prefix = [functional_group_prefix]

    pxe_rows = load_context(host)["rows"]
    matching_groups = set()
    for row in pxe_rows:
        group = _effective_group(row)
        for prefix in functional_group_prefix:
            if group.startswith(prefix):
                matching_groups.add(group)
                break

    nodes = []
    seen_ips = set()
    for row in pxe_rows:
        if _effective_group(row) in matching_groups:
            ip = row.get("ADMIN_IP", "")
            if ip and ip not in seen_ips:
                seen_ips.add(ip)
                nodes.append({
                    "admin_ip": ip,
                    "hostname": row.get("HOSTNAME", ""),
                    "functional_group": _effective_group(row),
                })
    return nodes


def get_non_target_nodes(host, functional_group_prefix: list[str] | str) -> list[dict[str, str]]:
    """Return nodes that do NOT match any of the functional_group_prefix values.

    Uses ``EXPECTED_FUNCTIONAL_GROUP`` for consistency with
    ``get_target_nodes``.

    Args:
        host: Testinfra host object
        functional_group_prefix: List of prefix strings or single string

    Returns:
        List of node info dicts for non-matching nodes
    """
    if isinstance(functional_group_prefix, str):
        functional_group_prefix = [functional_group_prefix]

    pxe_rows = load_context(host)["rows"]
    non_matching_groups = set()
    for row in pxe_rows:
        group = _effective_group(row)
        matched = False
        for prefix in functional_group_prefix:
            if group.startswith(prefix):
                matched = True
                break
        if not matched:
            non_matching_groups.add(group)

    nodes = []
    seen_ips = set()
    for row in pxe_rows:
        if _effective_group(row) in non_matching_groups:
            ip = row.get("ADMIN_IP", "")
            if ip and ip not in seen_ips:
                seen_ips.add(ip)
                nodes.append({
                    "admin_ip": ip,
                    "hostname": row.get("HOSTNAME", ""),
                    "functional_group": _effective_group(row),
                })
    return nodes


def resolve_node_key_value(host, node_ip: str, node_key: str) -> str:
    """Resolve the node-specific identifier value on a remote node.

    Args:
        host: Testinfra host object
        node_ip: Admin IP of the target node
        node_key: One of 'local_hostname', 'local_ipv4', 'instance_id'

    Returns:
        Resolved node identifier string, or empty string on failure
    """
    if node_key == "local_hostname":
        cmd = PXEBOOT_COMMANDS["pv_node_key_hostname"]
    elif node_key == "local_ipv4":
        cmd = PXEBOOT_COMMANDS["pv_node_key_ipv4"]
    elif node_key == "instance_id":
        cmd = PXEBOOT_COMMANDS["pv_node_key_instance"]
    else:
        cmd = PXEBOOT_COMMANDS["pv_node_key_hostname"]

    result = _run_on_node(host, node_ip, cmd)
    if result.rc == 0 and result.stdout.strip():
        return result.stdout.strip().split()[0]
    return ""


# =============================================================================
# iSCSI VERIFICATION FUNCTIONS
# =============================================================================


def verify_iscsi_service(host, node_ip: str) -> dict[str, Any]:
    """Check iscsid is active and enabled on a target node.

    Returns:
        {"success": bool, "error": str, "details": {"active": str, "enabled": str}}
    """
    active_cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_iscsid_active"])
    enabled_cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_iscsid_enabled"])

    active = active_cmd.stdout.strip()
    enabled = enabled_cmd.stdout.strip()

    success = active == "active" and enabled == "enabled"
    error = ""
    if not success:
        error = f"iscsid: active={active}, enabled={enabled} on {node_ip}"

    return {"success": success, "error": error, "details": {"active": active, "enabled": enabled}}


def verify_initiator_name(host, node_ip: str, expected_iqn: str) -> dict[str, Any]:
    """Validate iSCSI initiator name on a target node.

    Returns:
        {"success": bool, "error": str, "details": {"actual": str, "expected": str}}
    """
    cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_iscsi_initiator_read"] % POWERVAULT_ISCSI_INITIATOR_PATH)
    if cmd.rc != 0:
        return {
            "success": False,
            "error": f"Cannot read {POWERVAULT_ISCSI_INITIATOR_PATH} on {node_ip}",
            "details": {"actual": "", "expected": expected_iqn},
        }

    content = cmd.stdout.strip()
    expected_line = f"InitiatorName={expected_iqn}"
    found = expected_line in content

    return {
        "success": found,
        "error": "" if found else f"Expected '{expected_line}' in initiatorname.iscsi on {node_ip}",
        "details": {"actual": content, "expected": expected_iqn},
    }


def verify_iscsi_discovery(host, node_ip: str, ip_list: list[str], port: int) -> dict[str, Any]:
    """Check iSCSI discovery from all portal IPs.

    Returns:
        {"success": bool, "error": str, "details": {"discovered_iqn": str, "portal_results": list}}
    """
    discovered_iqn = ""
    portal_results = []

    for portal_ip in ip_list:
        cmd = _run_on_node(
            host, node_ip,
            PXEBOOT_COMMANDS["pv_iscsi_discovery"] % (portal_ip, port),
        )
        output = cmd.stdout.strip()
        iqn = ""
        if output:
            for line in output.split("\n"):
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1].startswith("iqn."):
                    iqn = parts[1]
                    break
        portal_results.append({
            "portal_ip": portal_ip,
            "rc": cmd.rc,
            "iqn": iqn,
            "output": output,
        })
        if iqn and not discovered_iqn:
            discovered_iqn = iqn

    success = bool(discovered_iqn)
    error = "" if success else f"No target IQN discovered from any portal on {node_ip}"

    return {
        "success": success,
        "error": error,
        "details": {"discovered_iqn": discovered_iqn, "portal_results": portal_results},
    }


def verify_iscsi_sessions(host, node_ip: str) -> dict[str, Any]:
    """Validate active iSCSI sessions on a target node.

    Returns:
        {"success": bool, "error": str, "details": {"session_count": int, "sessions": list}}
    """
    cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_iscsi_sessions"])
    output = cmd.stdout.strip()

    sessions = []
    if output:
        for line in output.split("\n"):
            line = line.strip()
            if line:
                sessions.append(line)

    session_count = len(sessions)
    success = session_count > 0
    error = "" if success else f"No active iSCSI sessions on {node_ip}"

    return {
        "success": success,
        "error": error,
        "details": {"session_count": session_count, "sessions": sessions},
    }


def verify_iscsi_startup_automatic(host, node_ip: str) -> dict[str, Any]:
    """Check that node.startup is set to automatic for iSCSI nodes.

    Returns:
        {"success": bool, "error": str, "details": {"startup_value": str}}
    """
    cmd = _run_on_node(
        host, node_ip,
        f"{PXEBOOT_COMMANDS['pv_iscsi_node_show']} 2>/dev/null | grep 'node.startup'",
    )
    output = cmd.stdout.strip()

    all_automatic = True
    found_any = False
    for line in output.split("\n"):
        line = line.strip()
        if "node.startup" in line:
            found_any = True
            if "automatic" not in line:
                all_automatic = False
                break

    success = found_any and all_automatic
    error = ""
    if not found_any:
        error = f"No node.startup entries found on {node_ip}"
    elif not all_automatic:
        error = f"node.startup is not 'automatic' on {node_ip}"

    return {
        "success": success,
        "error": error,
        "details": {"startup_value": output},
    }


def _get_portal_session_states(host, node_ip: str) -> dict[str, str]:
    """Parse 'iscsiadm -m session -P 1' to map each portal IP to its session state.

    Returns:
        dict mapping portal_ip -> session_state (e.g., "LOGGED_IN", "FREE", "TRANSPORT WAIT")
        Empty dict if no sessions found.
    """
    cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_iscsi_session_detail"])
    output = cmd.stdout.strip()
    if not output:
        return {}

    portal_states = {}
    current_portal_ip = None

    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("Current Portal:"):
            portal_part = line.split(":", 1)[1].strip()
            current_portal_ip = portal_part.split(":")[0].strip()
        elif "iSCSI Session State:" in line and current_portal_ip:
            state = line.split(":", 1)[1].strip()
            portal_states[current_portal_ip] = state

    return portal_states


def verify_portal_reachability(host, node_ip: str, ip_list: list[str], port: int) -> dict[str, Any]:
    """Test port connectivity and iSCSI session health from target node to each portal IP.

    Checks two things per portal:
    1. TCP port reachability (port open)
    2. iSCSI session state (must be LOGGED_IN)

    Returns:
        {"success": bool, "error": str, "details": {"results": list}}
    """
    results = []
    all_ok = True

    portal_states = _get_portal_session_states(host, node_ip)

    for portal_ip in ip_list:
        cmd = _run_on_node(
            host, node_ip,
            PXEBOOT_COMMANDS["pv_port_check"] % (POWERVAULT_PORT_CHECK_TIMEOUT, portal_ip, port),
        )
        reachable = "reachable" in cmd.stdout.strip()

        session_state = portal_states.get(portal_ip, "NO_SESSION")
        session_healthy = session_state == "LOGGED_IN"

        portal_ok = reachable and session_healthy
        results.append({
            "portal_ip": portal_ip,
            "reachable": reachable,
            "session_state": session_state,
            "session_healthy": session_healthy,
        })
        if not portal_ok:
            all_ok = False

    errors = []
    unreachable = [r["portal_ip"] for r in results if not r["reachable"]]
    unhealthy = [
        f"{r['portal_ip']} (state: {r['session_state']})"
        for r in results if not r["session_healthy"]
    ]
    if unreachable:
        errors.append(f"Unreachable portals from {node_ip}: {unreachable}")
    if unhealthy:
        errors.append(f"Unhealthy iSCSI sessions from {node_ip}: {unhealthy}")

    return {"success": all_ok, "error": "; ".join(errors), "details": {"results": results}}


# =============================================================================
# MULTIPATH VERIFICATION FUNCTIONS
# =============================================================================


def verify_multipath_service(host, node_ip: str) -> dict[str, Any]:
    """Check multipathd is active and enabled on a target node.

    Returns:
        {"success": bool, "error": str, "details": {"active": str, "enabled": str}}
    """
    active_cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_multipathd_active"])
    enabled_cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_multipathd_enabled"])

    active = active_cmd.stdout.strip()
    enabled = enabled_cmd.stdout.strip()

    success = active == "active" and enabled == "enabled"
    error = ""
    if not success:
        error = f"multipathd: active={active}, enabled={enabled} on {node_ip}"

    return {"success": success, "error": error, "details": {"active": active, "enabled": enabled}}


def verify_multipath_device(host, node_ip: str, volume_id: str) -> dict[str, Any]:
    """Find and validate multipath device matching volume_id.

    Mirrors the logic in setup_iscsi_storage.sh.j2 lines 98-121:
    1. grep volume_id
    2. fallback to DellEMC,ME5
    3. fallback to DellEMC,ME4
    4. fallback to latest dm-*

    Returns:
        {"success": bool, "error": str, "details": {"mpath_device": str, "match_method": str}}
    """
    cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_multipath_list"])
    output = cmd.stdout.strip()

    if not output:
        return {
            "success": False,
            "error": f"No multipath output on {node_ip}",
            "details": {"mpath_device": "", "match_method": ""},
        }

    mpath_device = ""
    match_method = ""

    if volume_id:
        for line in output.split("\n"):
            if volume_id.lower() in line.lower():
                parts = line.split()
                if parts:
                    mpath_device = parts[0]
                    match_method = "volume_id"
                    break

    if not mpath_device:
        for line in output.split("\n"):
            if "DellEMC,ME5" in line:
                parts = line.split()
                if parts:
                    mpath_device = parts[0]
                    match_method = "DellEMC,ME5"
                    break

    if not mpath_device:
        for line in output.split("\n"):
            if "DellEMC,ME4" in line:
                parts = line.split()
                if parts:
                    mpath_device = parts[0]
                    match_method = "DellEMC,ME4"
                    break

    if not mpath_device:
        dm_matches = re.findall(r"dm-\d+", output)
        if dm_matches:
            latest = sorted(dm_matches, key=lambda x: int(x.split("-")[1]))[-1]
            for line in output.split("\n"):
                if latest in line:
                    parts = line.split()
                    if parts:
                        mpath_device = parts[0]
                        match_method = "latest_dm"
                        break

    success = bool(mpath_device)
    error = "" if success else f"Unable to determine multipath device on {node_ip}"

    return {
        "success": success,
        "error": error,
        "details": {"mpath_device": mpath_device, "match_method": match_method},
    }


def verify_multipath_paths(
    host, node_ip: str, mpath_device: str, expected_paths: int,
) -> dict[str, Any]:
    """Verify multipath device has expected number of paths.

    Counts actual I/O path lines (``sd*`` devices) within the stanza for
    *mpath_device* in ``multipath -ll`` output.  Path lines contain a
    SCSI H:C:T:L address followed by the block device name, e.g.::

        |- 3:0:0:1 sdb 8:16 active ready running
        `- 4:0:0:1 sdc 8:32 active ready running

    Returns:
        {"success": bool, "error": str, "details": {"path_count": int}}
    """
    cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_multipath_list"])
    output = cmd.stdout.strip()

    # Isolate the stanza for the target device: from the header line
    # containing mpath_device up to the next device header or end-of-output.
    # Device header lines start at column 0 with the alias (e.g., "mpatha (...)")
    # and always contain a WWID in parentheses.  Non-header body lines include
    # detail lines like "size=..." as well as tree-prefixed path lines.
    in_stanza = False
    path_count = 0
    _DEVICE_HEADER_RE = re.compile(r"^\S+\s+\(")
    for line in output.split("\n"):
        if not line.strip():
            continue
        is_device_header = bool(_DEVICE_HEADER_RE.match(line))
        if is_device_header:
            in_stanza = mpath_device in line
            continue
        if in_stanza:
            # Path lines contain a SCSI H:C:T:L address (e.g. 3:0:0:1)
            # followed by a block device like sdb/sdc.
            parts = line.strip().lstrip("|-`+\\ ").split()
            if len(parts) >= 2 and ":" in parts[0] and parts[1].startswith("sd"):
                path_count += 1

    success = path_count >= expected_paths
    error = (
        "" if success
        else f"Expected {expected_paths} paths, found {path_count} on {node_ip}"
    )

    return {
        "success": success,
        "error": error,
        "details": {"path_count": path_count},
    }


# =============================================================================
# MOUNT VERIFICATION FUNCTIONS
# =============================================================================


def verify_gpt_partition(host, node_ip: str, mpath_device: str, expect_gpt: bool = True) -> dict[str, Any]:
    """Verify GPT label *and* partition 1 exist on multipath device.

    Parses ``parted -s <dev> print`` output.  Requires both:
    - ``Partition Table: gpt``
    - A numbered partition line starting with ``1`` (e.g.
      ``1  1049kB  1000GB  1000GB  xfs  primary``)

    Args:
        expect_gpt: If False, the test expects NO GPT label (negative test)

    Returns:
        {"success": bool, "error": str, "details": {"partition_device": str}}
    """
    part_dev = f"/dev/mapper/{mpath_device}1"
    cmd = _run_on_node(
        host, node_ip,
        PXEBOOT_COMMANDS["pv_parted_print"] % mpath_device,
    )
    output = cmd.stdout.strip()

    has_gpt = "gpt" in output.lower()
    # Partition lines start with a number after optional whitespace.
    has_part1 = any(
        line.strip().startswith("1")
        and len(line.split()) >= 3
        for line in output.split("\n")
    )
    
    if expect_gpt:
        success = has_gpt and has_part1
        if not has_gpt:
            error = f"No GPT label on {mpath_device} on {node_ip}"
        elif not has_part1:
            error = f"GPT label present but partition 1 missing on {mpath_device} on {node_ip}"
        else:
            error = ""
    else:
        # Negative test: expect NO GPT label
        success = not has_gpt
        error = f"Expected no GPT label but found GPT on {mpath_device} on {node_ip}" if has_gpt else ""

    return {
        "success": success,
        "error": error,
        "details": {"partition_device": part_dev, "parted_output": output},
    }


def verify_filesystem_type(host, node_ip: str, device: str, expected_fs: str) -> dict[str, Any]:
    """Verify filesystem formatted with correct type.

    Returns:
        {"success": bool, "error": str, "details": {"actual_fs": str}}
    """
    cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_blkid_fstype"] % device)
    actual_fs = cmd.stdout.strip()

    success = actual_fs == expected_fs
    error = "" if success else f"Expected fs_type {expected_fs}, found {actual_fs} on {node_ip}"

    return {
        "success": success,
        "error": error,
        "details": {"actual_fs": actual_fs},
    }


def verify_mount_point_exists(host, node_ip: str, mount_point: str) -> dict[str, Any]:
    """Verify mount point directory exists.

    Returns:
        {"success": bool, "error": str, "details": {}}
    """
    cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_dir_exists"] % mount_point)
    exists = cmd.stdout.strip() == "exists"

    success = exists
    error = "" if success else f"Mount point directory {mount_point} does not exist on {node_ip}"

    return {
        "success": success,
        "error": error,
        "details": {},
    }


def verify_volume_mounted(host, node_ip: str, mount_point: str) -> dict[str, Any]:
    """Verify PowerVault volume is actively mounted.

    Returns:
        {"success": bool, "error": str, "details": {}}
    """
    cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_mountpoint_check"] % mount_point)
    mounted = cmd.stdout.strip() == "mounted"

    success = mounted
    error = "" if success else f"Volume not mounted at {mount_point} on {node_ip}"

    return {
        "success": success,
        "error": error,
        "details": {},
    }


def _kernel_visible_opts(opts_str: str) -> set[str]:
    """Return the subset of mount options that appear in /proc/mounts.

    ``defaults`` is a mount(8) shorthand for ``rw,suid,dev,exec,auto,nouser,
    async`` — it never appears literally in /proc/mounts.  ``_netdev`` is a
    userspace scheduling hint consumed by systemd/mount and likewise absent
    from the kernel mount table.  This helper strips those so the comparison
    only covers options the kernel actually records.
    """
    _USERSPACE_ONLY = frozenset({"defaults", "_netdev", "auto", "noauto", "user", "nouser"})
    return {
        opt for opt in opts_str.split(",")
        if opt and opt not in _USERSPACE_ONLY
    }


def verify_mount_options(
    host, node_ip: str, mount_point: str, expected_opts: str,
) -> dict[str, Any]:
    """Verify mount options applied correctly.

    Compares only kernel-visible options: userspace-only hints like
    ``defaults`` and ``_netdev`` are stripped from the expected set
    before matching against /proc/mounts.  The actual options from
    /proc/mounts must be a superset of the expected kernel-visible
    options (the kernel may add additional defaults like ``relatime``).

    Returns:
        {"success": bool, "error": str, "details": {"actual_opts": str}}
    """
    cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_proc_mounts_read"])
    output = cmd.stdout.strip()

    actual_opts = ""
    for line in output.split("\n"):
        parts = line.split()
        if len(parts) >= 4 and parts[1] == mount_point:
            actual_opts = parts[3]
            break

    expected_set = _kernel_visible_opts(expected_opts)
    actual_set = set(actual_opts.split(",")) if actual_opts else set()
    missing = expected_set - actual_set
    success = not missing and bool(actual_opts)
    if not actual_opts:
        error = f"Mount point {mount_point} not found in /proc/mounts on {node_ip}"
    elif missing:
        error = (
            f"Missing mount opts {','.join(sorted(missing))} on "
            f"{mount_point} on {node_ip} (actual: {actual_opts})"
        )
    else:
        error = ""

    return {
        "success": success,
        "error": error,
        "details": {"actual_opts": actual_opts},
    }


def verify_fstab_entry(host, node_ip: str, mount_point: str) -> dict[str, Any]:
    """Verify persistent fstab entry exists.

    Returns:
        {"success": bool, "error": str, "details": {"fstab_line": str}}
    """
    cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_fstab_read"])
    output = cmd.stdout.strip()

    found = False
    fstab_line = ""
    for line in output.split("\n"):
        if mount_point in line and not line.strip().startswith("#"):
            found = True
            fstab_line = line
            break

    success = found
    error = "" if success else f"No fstab entry for {mount_point} on {node_ip}"

    return {
        "success": success,
        "error": error,
        "details": {"fstab_line": fstab_line},
    }


# =============================================================================
# BIND MOUNT VERIFICATION FUNCTIONS
# =============================================================================


def verify_node_subdirectory(host, node_ip: str, mount_point: str, node_key: str) -> dict[str, Any]:
    """Verify per-node subdirectory exists under mount point.

    Returns:
        {"success": bool, "error": str, "details": {"node_subdir": str}}
    """
    node_value = resolve_node_key_value(host, node_ip, node_key)
    if not node_value:
        return {
            "success": False,
            "error": f"Unable to resolve node_key {node_key} on {node_ip}",
            "details": {"node_subdir": ""},
        }

    node_subdir = f"{mount_point}/{node_value}"
    cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_dir_exists"] % node_subdir)
    exists = cmd.stdout.strip() == "exists"

    success = exists
    error = "" if success else f"Node subdirectory {node_subdir} does not exist on {node_ip}"

    return {
        "success": success,
        "error": error,
        "details": {"node_subdir": node_subdir, "node_value": node_value},
    }


def verify_bind_mounts(host, node_ip: str, mount_point: str, node_key: str, bind_targets: list[str]) -> dict[str, Any]:
    """Verify bind mount targets are active.

    Returns:
        {"success": bool, "error": str, "details": {"bind_status": dict}}
    """
    node_value = resolve_node_key_value(host, node_ip, node_key)
    if not node_value:
        return {
            "success": False,
            "error": f"Unable to resolve node_key {node_key} on {node_ip}",
            "details": {"bind_status": {}},
        }

    bind_status = {}
    all_ok = True
    for target in bind_targets:
        target_stripped = target.lstrip("/")
        bind_source = f"{mount_point}/{node_value}/{target_stripped}"
        cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_mountpoint_check"] % target)
        mounted = cmd.stdout.strip() == "mounted"
        bind_status[target] = mounted
        if not mounted:
            all_ok = False

    success = all_ok
    error = "" if success else f"Some bind mounts not active on {node_ip}"

    return {
        "success": success,
        "error": error,
        "details": {"bind_status": bind_status},
    }


def verify_bind_fstab_entries(host, node_ip: str, mount_point: str, node_key: str, bind_targets: list[str]) -> dict[str, Any]:
    """Verify bind mount fstab entries are persistent.

    Returns:
        {"success": bool, "error": str, "details": {"fstab_status": dict}}
    """
    node_value = resolve_node_key_value(host, node_ip, node_key)
    if not node_value:
        return {
            "success": False,
            "error": f"Unable to resolve node_key {node_key} on {node_ip}",
            "details": {"fstab_status": {}},
        }

    cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_fstab_read"])
    output = cmd.stdout.strip()

    fstab_status = {}
    all_ok = True
    for target in bind_targets:
        target_stripped = target.lstrip("/")
        bind_source = f"{mount_point}/{node_value}/{target_stripped}"
        found = any(bind_source in line and target in line for line in output.split("\n"))
        fstab_status[target] = found
        if not found:
            all_ok = False

    success = all_ok
    error = "" if success else f"Some bind fstab entries missing on {node_ip}"

    return {
        "success": success,
        "error": error,
        "details": {"fstab_status": fstab_status},
    }


def verify_bind_isolation(
    host,
    mount_point: str,
    node_key: str,
    bind_targets: list[str],
    target_nodes: list[dict[str, str]],
) -> dict[str, Any]:
    """Verify per-node data separation via bind mounts.

    Performs a real cross-node write/read isolation test:

    1. Resolve each node's identity (``node_key`` → ``node_value``).
    2. For the first configured bind target, each node writes a unique
       marker to its bind-mounted path.
    3. From the OIM, verify each node's PV-backing subdirectory
       contains *only* that node's marker and none of the others.
    4. Clean up all markers.

    Falls back to a directory-existence check when fewer than two
    nodes are available (isolation is meaningless with a single node).

    Returns:
        {"success": bool, "error": str, "details": {…}}
    """
    _MARKER_PREFIX = ".pv_isolation_test"
    failures: list[str] = []
    node_info: list[dict[str, str]] = []

    # Phase 1: resolve node values and verify subdirectories exist
    for node in target_nodes:
        node_ip = node["admin_ip"]
        nv = resolve_node_key_value(host, node_ip, node_key)
        if not nv:
            failures.append(
                f"Cannot resolve node_key {node_key} on {node_ip}"
            )
            continue
        subdir = f"{mount_point}/{nv}"
        cmd = _run_on_node(
            host, node_ip,
            PXEBOOT_COMMANDS["pv_dir_exists"] % subdir,
        )
        if cmd.stdout.strip() != "exists":
            failures.append(
                f"Isolation subdir {subdir} missing on {node_ip}"
            )
            continue
        node_info.append({
            "ip": node_ip,
            "node_value": nv,
            "subdir": subdir,
        })

    if failures:
        return {
            "success": False,
            "error": "; ".join(failures),
            "details": {"node_info": node_info},
        }

    # With <2 nodes isolation is trivially satisfied; verify subdir only
    if len(node_info) < 2:
        return {
            "success": True,
            "error": "",
            "details": {"node_info": node_info, "note": "single node"},
        }

    # Pick the first bind target for the isolation probe
    probe_target = bind_targets[0] if bind_targets else None
    if not probe_target:
        return {
            "success": True,
            "error": "",
            "details": {
                "node_info": node_info,
                "note": "no bind targets to probe",
            },
        }

    # Phase 2: each node writes a unique marker via its bind mount
    marker_name = f"{_MARKER_PREFIX}_{id(host)}"
    for ni in node_info:
        token = f"isolation_{ni['node_value']}"
        marker_path = f"{probe_target}/{marker_name}"
        cmd_str = f"echo {token} > {marker_path}"
        _run_on_node(host, ni["ip"], cmd_str)

    # Phase 3: cross-check from OIM via the PV backing paths
    try:
        for ni in node_info:
            expected_token = f"isolation_{ni['node_value']}"
            target_stripped = probe_target.lstrip("/")
            backing = (
                f"{ni['subdir']}/{target_stripped}/{marker_name}"
            )
            # Read this node's marker from the PV backing store
            read_cmd = _run_on_node(
                host, ni["ip"], f"cat {backing} 2>/dev/null",
            )
            actual = read_cmd.stdout.strip()
            if actual != expected_token:
                failures.append(
                    f"{ni['ip']}: marker mismatch in {backing} "
                    f"(expected '{expected_token}', "
                    f"got '{actual}')"
                )
                continue

            # Verify other nodes' markers are NOT visible
            for other in node_info:
                if other["ip"] == ni["ip"]:
                    continue
                other_stripped = probe_target.lstrip("/")
                other_backing = (
                    f"{other['subdir']}/{other_stripped}"
                    f"/{marker_name}"
                )
                # Read via the OIM to check the PV backing path
                peek = _run_on_node(
                    host, ni["ip"],
                    f"cat {other_backing} 2>/dev/null",
                )
                peek_val = peek.stdout.strip()
                if peek_val == expected_token:
                    failures.append(
                        f"{ni['ip']}: can read own marker "
                        f"from {other['ip']}'s backing path "
                        f"{other_backing} — isolation breach"
                    )
    finally:
        # Phase 4: clean up markers
        for ni in node_info:
            marker_path = f"{probe_target}/{marker_name}"
            _run_on_node(
                host, ni["ip"], f"rm -f {marker_path}",
            )

    return {
        "success": not failures,
        "error": "; ".join(failures) if failures else "",
        "details": {"node_info": node_info},
    }


# =============================================================================
# CLOUD-INIT VERIFICATION FUNCTIONS
# =============================================================================


def verify_setup_log(host, node_ip: str, pv_name: str) -> dict[str, Any]:
    """Check cloud-init runcmd log exists and shows completion.

    Returns:
        {"success": bool, "error": str, "details": {"log_exists": bool, "complete": bool, "errors": list}}
    """
    log_path = POWERVAULT_LOG_TEMPLATE.format(name=pv_name)

    exists_cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_log_exists"] % log_path)
    log_exists = exists_cmd.stdout.strip() == "exists"

    if not log_exists:
        return {
            "success": False,
            "error": f"Setup log {log_path} does not exist on {node_ip}",
            "details": {"log_exists": False, "complete": False, "errors": []},
        }

    complete_cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_log_complete"] % (POWERVAULT_LOG_COMPLETE_MSG, log_path))
    complete = "found" in complete_cmd.stdout.strip()

    error_cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_log_errors"] % log_path)
    error_lines = [l.strip() for l in error_cmd.stdout.strip().split("\n") if l.strip()]

    success = log_exists and complete and len(error_lines) == 0

    return {
        "success": success,
        "error": "" if success else f"Setup log issues on {node_ip}: exists={log_exists}, complete={complete}, errors={len(error_lines)}",
        "details": {"log_exists": log_exists, "complete": complete, "errors": error_lines},
    }


def verify_cloud_init_groups_dict(host, pv_entry: dict, target_nodes: list[dict]) -> dict[str, Any]:
    """Verify the 2.3 metadata-service generated iSCSI setup script for a PV entry.

    Asserts that every target node received the rendered
    ``/usr/local/bin/setup_iscsi_storage_<name>.sh`` with the correct
    portal IPs and PV name marker.  This tests the *generated* metadata
    state — not the source-tree Ansible templates.

    Args:
        host: Testinfra host object
        pv_entry: A single powervault_config entry dict
        target_nodes: List of node dicts (from get_target_nodes) with admin_ip

    Returns:
        {"success": bool, "error": str, "details": {…}}
    """
    pv_name = pv_entry.get("name", "")
    script_path = f"/usr/local/bin/setup_iscsi_storage_{pv_name}.sh"
    portal_ips = pv_entry.get("ip", [])

    details: dict[str, Any] = {"script_path": script_path, "nodes": {}}
    failures: list[str] = []

    for node in target_nodes:
        node_ip = node["admin_ip"]
        label = node.get("hostname") or node_ip

        # Check script exists and is executable
        probe = _run_on_node(
            host, node_ip,
            f"test -f {script_path} && test -x {script_path} && echo ok || echo missing",
        )
        script_ok = probe.stdout.strip() == "ok"

        if not script_ok:
            details["nodes"][label] = {"present": False}
            failures.append(f"{label}: {script_path} missing or not executable")
            continue

        # Read script content and verify expected markers
        content_cmd = _run_on_node(host, node_ip, f"cat {script_path}")
        content = content_cmd.stdout if content_cmd.rc == 0 else ""

        name_marker = f"setup complete for {pv_name}" in content
        portal_found = [ip for ip in portal_ips if ip in content]

        node_detail: dict[str, Any] = {
            "present": True,
            "name_marker": name_marker,
            "portals_found": len(portal_found),
            "portals_expected": len(portal_ips),
        }
        details["nodes"][label] = node_detail

        if not name_marker:
            failures.append(
                f"{label}: script missing PV name marker '{pv_name}'"
            )
        if portal_ips and len(portal_found) < len(portal_ips):
            missing = [ip for ip in portal_ips if ip not in content]
            failures.append(
                f"{label}: missing portal IPs in script: {', '.join(missing)}"
            )

    return {
        "success": not failures,
        "error": "; ".join(failures) if failures else "",
        "details": details,
    }


# =============================================================================
# MISC VERIFICATION FUNCTIONS
# =============================================================================


def verify_no_duplicate_fstab(host, node_ip: str, expect_duplicates: bool = False) -> dict[str, Any]:
    """Verify no duplicate fstab entries.

    Args:
        expect_duplicates: If True, the test expects duplicates to be found (negative test)

    Returns:
        {"success": bool, "error": str, "details": {"duplicate_count": int}}
    """
    cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_fstab_read"])
    output = cmd.stdout.strip()

    lines = [line.strip() for line in output.split("\n") if line.strip() and not line.strip().startswith("#")]
    unique_lines = set(lines)
    duplicate_count = len(lines) - len(unique_lines)

    if expect_duplicates:
        # Negative test: expect duplicates to be found
        success = duplicate_count > 0
        error = f"Expected duplicates but found none on {node_ip}" if duplicate_count == 0 else ""
    else:
        # Positive test: expect no duplicates
        success = duplicate_count == 0
        error = "" if success else f"Found {duplicate_count} duplicate fstab entries on {node_ip}"

    return {
        "success": success,
        "error": error,
        "details": {"duplicate_count": duplicate_count},
    }


def verify_all_mounts_writable(
    host, node_ip: str, mount_point: str,
    node_key: str | None = None,
    bind_targets: list[str] | None = None,
) -> dict[str, Any]:
    """Verify all PV mounts (main + node subdir + bind targets) are writable.

    Checks:
    - The main mount point
    - The per-node subdirectory (when *node_key* is set)
    - Every configured bind-mount target path in *bind_targets*

    Returns:
        {"success": bool, "error": str, "details": {"writable_status": dict}}
    """
    writable_status: dict[str, bool] = {}
    all_ok = True
    _W_CMD = "test -w %s && echo writable || echo not_writable"

    # Check main mount point
    cmd = _run_on_node(host, node_ip, _W_CMD % mount_point)
    main_writable = cmd.stdout.strip() == "writable"
    writable_status[mount_point] = main_writable
    if not main_writable:
        all_ok = False

    # Check node subdirectory if node_key is set
    if node_key:
        node_value = resolve_node_key_value(host, node_ip, node_key)
        if node_value:
            node_subdir = f"{mount_point}/{node_value}"
            cmd = _run_on_node(
                host, node_ip, _W_CMD % node_subdir,
            )
            subdir_writable = cmd.stdout.strip() == "writable"
            writable_status[node_subdir] = subdir_writable
            if not subdir_writable:
                all_ok = False

    # Check each bind-mount target path
    for bt in bind_targets or []:
        cmd = _run_on_node(host, node_ip, _W_CMD % bt)
        bt_writable = cmd.stdout.strip() == "writable"
        writable_status[bt] = bt_writable
        if not bt_writable:
            all_ok = False

    not_writable = [p for p, w in writable_status.items() if not w]
    error = (
        "" if all_ok
        else f"Not writable on {node_ip}: {', '.join(not_writable)}"
    )

    return {
        "success": all_ok,
        "error": error,
        "details": {"writable_status": writable_status},
    }


def verify_permissions(host, node_ip: str, path: str, expected_owner: str, expected_group: str, expected_mode: str) -> dict[str, Any]:
    """Verify permissions on a path.

    Returns:
        {"success": bool, "error": str, "details": {"actual": str}}
    """
    cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_permissions_check"] % path)
    actual = cmd.stdout.strip()
    # Normalize expected mode: stat returns '750' not '0750', so strip leading zero
    expected_mode_normalized = expected_mode.lstrip("0") or "0"
    expected = f"{expected_owner}:{expected_group}:{expected_mode_normalized}"

    success = actual == expected
    error = "" if success else f"Expected permissions {expected}, found {actual} on {node_ip}"

    return {
        "success": success,
        "error": error,
        "details": {"actual": actual, "expected": expected},
    }


# =============================================================================
# I/O VERIFICATION FUNCTIONS
# =============================================================================


def verify_io_write_read(
    host, node_ip: str, path: str,
) -> dict[str, Any]:
    """Write a test file, read it back, verify content, and clean up.

    Creates ``<path>/.pv_io_test_<pid>`` with a known payload, reads it
    back, and removes the file.  Proves the mount is usable for real I/O
    (not just stat-level checks).

    Returns:
        {"success": bool, "error": str, "details": {…}}
    """
    marker = "omnia_pv_io_verify"
    test_file = f"{path}/.pv_io_test_$$"
    write_cmd = (
        f"f={test_file} && echo {marker} > \"$f\" "
        f"&& cat \"$f\" && rm -f \"$f\""
    )
    cmd = _run_on_node(host, node_ip, write_cmd)
    readback = cmd.stdout.strip() if cmd.rc == 0 else ""
    success = readback == marker

    if cmd.rc != 0:
        error = f"I/O write/read failed (rc={cmd.rc}) at {path} on {node_ip}"
    elif readback != marker:
        error = (
            f"I/O readback mismatch at {path} on {node_ip}: "
            f"expected '{marker}', got '{readback}'"
        )
    else:
        error = ""

    return {
        "success": success,
        "error": error,
        "details": {"path": path, "readback": readback},
    }


def verify_bind_io(
    host, node_ip: str, mount_point: str, node_key: str,
    bind_target: str,
) -> dict[str, Any]:
    """Write through a bind mount and verify the data lands on the PV.

    Writes a token to ``<bind_target>/.<testfile>``, then reads the
    same file from the backing PV path
    ``<mount_point>/<node_value><bind_target>/.<testfile>`` to prove
    the bind mount is functional, not just present.

    Returns:
        {"success": bool, "error": str, "details": {…}}
    """
    node_value = resolve_node_key_value(host, node_ip, node_key)
    if not node_value:
        return {
            "success": False,
            "error": f"Cannot resolve node_key {node_key} on {node_ip}",
            "details": {},
        }

    marker = "omnia_bind_io_verify"
    test_name = ".pv_bind_io_test_$$"
    bind_file = f"{bind_target}/{test_name}"
    backing_file = f"{mount_point}/{node_value}{bind_target}/{test_name}"
    cmd_str = (
        f"echo {marker} > {bind_file} "
        f"&& cat {backing_file} "
        f"&& rm -f {bind_file}"
    )
    cmd = _run_on_node(host, node_ip, cmd_str)
    readback = cmd.stdout.strip() if cmd.rc == 0 else ""
    success = readback == marker

    if cmd.rc != 0:
        error = (
            f"Bind I/O failed (rc={cmd.rc}) for "
            f"{bind_target} on {node_ip}"
        )
    elif readback != marker:
        error = (
            f"Bind readback mismatch: wrote to {bind_file}, "
            f"read from {backing_file} on {node_ip}: "
            f"expected '{marker}', got '{readback}'"
        )
    else:
        error = ""

    return {
        "success": success,
        "error": error,
        "details": {
            "bind_target": bind_target,
            "backing_path": backing_file,
            "readback": readback,
        },
    }


# Mandatory Slurm/MySQL bind-mount targets that 2.3 documents for
# PowerVault-backed control-plane nodes.
SLURM_MANDATORY_BIND_TARGETS: tuple[str, ...] = (
    "/var/lib/mysql",
    "/var/spool/slurm",
)
