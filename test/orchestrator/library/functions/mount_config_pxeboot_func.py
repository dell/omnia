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

"""NFS mount_config functional verification after PXE boot.

Validates that NFS mounts defined in storage_config.yml are correctly
applied on provisioned nodes: mount point exists, volume is mounted,
mount options match, fstab entries are persistent, bind mounts are active,
per-node isolation directories exist, functional-group targeting is correct,
permissions are applied, and the OIM-side mount is active.
"""

import os
import re
from typing import Any

from ..vars.pxeboot_vars import (
    OMNIA_CONFIG,
    PXEBOOT_COMMANDS,
    STORAGE_CONFIG,
)
from ._pxeboot_helpers import (
    group_fields,
    load_runtime_context,
    load_workload_context,
    remote_command,
    rows_matching,
    runtime_exception,
    runtime_result,
)
from ._prepare_helpers import read_yaml_mapping
from ._workload_helpers import optional_skip as _skip
from .project_func import (
    resolve_target_input_project_path,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_storage_config(host) -> dict[str, Any]:
    """Load storage_config.yml from the project input directory."""
    input_dir = resolve_target_input_project_path(host)
    path = os.path.join(input_dir, STORAGE_CONFIG)
    return read_yaml_mapping(host, path)


def _effective_mounts(
    host,
    storage_config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return the production-equivalent effective mount set.

    Replicates the filtering logic from ``mount_config/tasks/main.yml``:
    1. Select entries from ``mounts:`` that have a ``source`` (excludes
       powervault_config and malformed entries).
    2. Load ``omnia_config.yml`` and resolve ``vast_storage_name``.
    3. Identify entries named ``vast_storage`` and exclude them when the
       configured ``vast_storage_name`` does not reference them.
    """
    mounts = storage_config.get("mounts")
    if not isinstance(mounts, list):
        return []
    all_mounts = [
        m for m in mounts
        if isinstance(m, dict) and m.get("source")
    ]

    # Resolve configured VAST storage name from omnia_config.yml
    input_dir = resolve_target_input_project_path(host)
    omnia_path = os.path.join(input_dir, OMNIA_CONFIG)
    try:
        omnia_config = read_yaml_mapping(host, omnia_path)
    except (OSError, ValueError, TypeError):
        omnia_config = {}

    slurm_clusters = omnia_config.get("slurm_cluster")
    if isinstance(slurm_clusters, list) and slurm_clusters:
        active_cluster = slurm_clusters[0] if slurm_clusters else {}
    else:
        active_cluster = {}
    if not isinstance(active_cluster, dict):
        active_cluster = {}

    configured_vast = str(
        active_cluster.get("vast_storage_name") or ""
    ).strip()

    # Identify VAST-managed entries (name == "vast_storage")
    managed_vast_names = list({
        m["name"] for m in all_mounts
        if m.get("name") == "vast_storage"
    })

    # Disabled VAST entries: managed names not matching the configured one
    disabled_vast = [
        name for name in managed_vast_names
        if name != configured_vast
    ]

    # Filter out disabled VAST entries
    return [
        m for m in all_mounts
        if m.get("name") not in disabled_vast
    ]


def _resolve_mount_params(
    mount_item: dict[str, Any],
    mount_params: dict[str, Any],
) -> dict[str, str]:
    """Resolve effective mount fields using profile fallback."""
    profile_name = mount_item.get("mount_params", "")
    profile = mount_params.get(profile_name, {}) if profile_name else {}
    if not isinstance(profile, dict):
        profile = {}
    return {
        "fs_type": str(
            mount_item.get("fs_type", profile.get("fs_type", "auto"))
        ),
        "mnt_opts": str(
            mount_item.get("mnt_opts", profile.get("mnt_opts", "defaults"))
        ),
        "dump_freq": str(
            mount_item.get("dump_freq", profile.get("dump_freq", "0"))
        ),
        "fsck_pass": str(
            mount_item.get("fsck_pass", profile.get("fsck_pass", "0"))
        ),
    }


# NFS options silently dropped by modern kernels (RHEL 10+ / kernel 6.x+).
# These must not cause a comparison failure.
_DEPRECATED_NFS_OPTIONS = {"intr", "nointr"}

# Options that are fstab/userspace directives and do NOT appear in
# /proc/mounts.  These must be validated against /etc/fstab instead.
_FSTAB_ONLY_OPTIONS = {"defaults", "nofail", "_netdev", "noauto", "x-systemd.automount"}


def _target_rows(
    context: dict[str, Any],
    mount_item: dict[str, Any],
) -> list[dict[str, str]]:
    """Select mapping rows targeted by this mount entry.

    Supports both ``functional_group_prefix`` (FG name prefix match) and
    ``groups`` (exact PXE GROUP_NAME match).  The two are mutually exclusive
    in ``storage_config.yml``.  When neither is present the mount is assumed
    to target every mapped node.
    """
    prefixes = mount_item.get("functional_group_prefix")
    if isinstance(prefixes, list) and prefixes:
        prefix_tuple = tuple(str(p) for p in prefixes)
        return rows_matching(context, prefix_tuple)

    groups = mount_item.get("groups")
    if isinstance(groups, list) and groups:
        group_set = {str(g) for g in groups}
        return [
            row for row in context["rows"]
            if row.get("GROUP_NAME", "") in group_set
        ]

    return context["rows"]


def _non_target_rows(
    context: dict[str, Any],
    mount_item: dict[str, Any],
) -> list[dict[str, str]]:
    """Select mapping rows NOT targeted by this mount entry."""
    targeted = _target_rows(context, mount_item)
    targeted_hosts = {row["HOSTNAME"] for row in targeted}

    # When neither prefix nor groups is set, all nodes are targeted
    prefixes = mount_item.get("functional_group_prefix")
    groups = mount_item.get("groups")
    has_targeting = (
        (isinstance(prefixes, list) and bool(prefixes))
        or (isinstance(groups, list) and bool(groups))
    )
    if not has_targeting:
        return []

    return [
        row for row in context["rows"]
        if row["HOSTNAME"] not in targeted_hosts
    ]


# ---------------------------------------------------------------------------
# Public check functions
# ---------------------------------------------------------------------------


def check_mount_config_mount_point(host):
    """Verify NFS mount point directories exist on all target nodes."""
    summary = "NFS mount point directory"
    try:
        context = load_runtime_context(host)
        storage_config = _load_storage_config(host)
        mounts = _effective_mounts(host, storage_config)
        if not mounts:
            return _skip(summary, "No NFS mounts configured in storage_config.yml")

        outcomes = {}
        for mount_item in mounts:
            mount_point = mount_item.get("mount_point", "")
            if not mount_point:
                continue
            rows = _target_rows(context, mount_item)
            for row in rows:
                cmd = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["mount_config_dir_exists"] % mount_point,
                )
                key = f"{row['HOSTNAME']}:{mount_point}"
                if cmd.rc == 0 and "exists" in cmd.stdout.strip().lower():
                    outcomes[key] = (True, f"{mount_point} exists")
                else:
                    outcomes[key] = (False, f"{mount_point} not found")

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("Mapped mounts", len(outcomes))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Missing mount points: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_mount_config_volume_mounted(host):
    """Verify NFS volumes are actively mounted on all target nodes."""
    summary = "NFS volume mounted"
    try:
        context = load_runtime_context(host)
        storage_config = _load_storage_config(host)
        mounts = _effective_mounts(host, storage_config)
        if not mounts:
            return _skip(summary, "No NFS mounts configured in storage_config.yml")

        outcomes = {}
        for mount_item in mounts:
            mount_point = mount_item.get("mount_point", "")
            if not mount_point:
                continue
            rows = _target_rows(context, mount_item)
            for row in rows:
                cmd = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["mount_config_mountpoint_check"]
                    % mount_point,
                )
                key = f"{row['HOSTNAME']}:{mount_point}"
                output = cmd.stdout.strip().upper()
                if output == "MOUNTED":
                    outcomes[key] = (True, "mounted")
                else:
                    outcomes[key] = (False, "not mounted")

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("Mapped mounts", len(outcomes))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Not mounted: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_mount_config_mount_options(host):
    """Verify NFS mount options match storage_config.yml profile on nodes.

    Kernel-visible options are validated against ``/proc/mounts``.
    Fstab-only / userspace directives (``defaults``, ``nofail``,
    ``_netdev``, ``noauto``) are validated against ``/etc/fstab``.
    Deprecated NFS options (``intr``, ``nointr``) are excluded from both.
    """
    summary = "NFS mount options"
    try:
        context = load_runtime_context(host)
        storage_config = _load_storage_config(host)
        mounts = _effective_mounts(host, storage_config)
        mount_params = storage_config.get("mount_params", {})
        if not isinstance(mount_params, dict):
            mount_params = {}
        if not mounts:
            return _skip(summary, "No NFS mounts configured in storage_config.yml")

        outcomes = {}
        for mount_item in mounts:
            mount_point = mount_item.get("mount_point", "")
            if not mount_point:
                continue
            resolved = _resolve_mount_params(mount_item, mount_params)
            expected_opts = resolved["mnt_opts"]

            all_expected = (
                set(expected_opts.split(",")) - _DEPRECATED_NFS_OPTIONS
            )
            # Split into kernel-visible and fstab-only sets
            fstab_expected = all_expected & _FSTAB_ONLY_OPTIONS
            kernel_expected = all_expected - _FSTAB_ONLY_OPTIONS

            rows = _target_rows(context, mount_item)
            for row in rows:
                key = f"{row['HOSTNAME']}:{mount_point}"
                problems = []

                # --- Kernel options: check /proc/mounts ---
                proc_cmd = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["mount_config_proc_mounts"],
                )
                actual_kernel_opts = ""
                for line in proc_cmd.stdout.strip().split("\n"):
                    parts = line.split()
                    if len(parts) >= 4 and parts[1] == mount_point:
                        actual_kernel_opts = parts[3]
                        break
                if not actual_kernel_opts:
                    problems.append("mount not found in /proc/mounts")
                elif kernel_expected:
                    actual_set = set(actual_kernel_opts.split(","))
                    missing_kernel = kernel_expected - actual_set
                    if missing_kernel:
                        problems.append(
                            f"/proc/mounts missing: "
                            f"{','.join(sorted(missing_kernel))}"
                        )

                # --- Fstab-only options: check /etc/fstab ---
                if fstab_expected:
                    fstab_cmd = remote_command(
                        host, row,
                        PXEBOOT_COMMANDS["mount_config_fstab_read"],
                    )
                    fstab_opts = ""
                    for line in fstab_cmd.stdout.strip().split("\n"):
                        fields_line = line.split()
                        if (
                            len(fields_line) >= 4
                            and not line.startswith("#")
                            and fields_line[1] == mount_point
                        ):
                            fstab_opts = fields_line[3]
                            break
                    if not fstab_opts:
                        problems.append(
                            f"fstab entry not found for {mount_point}"
                        )
                    else:
                        fstab_set = set(fstab_opts.split(","))
                        missing_fstab = fstab_expected - fstab_set
                        if missing_fstab:
                            problems.append(
                                f"/etc/fstab missing: "
                                f"{','.join(sorted(missing_fstab))}"
                            )

                if problems:
                    outcomes[key] = (False, "; ".join(problems))
                else:
                    outcomes[key] = (True, actual_kernel_opts)

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("Mapped mounts", len(outcomes))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Options mismatch: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_mount_config_fstab(host):
    """Verify NFS fstab entries are persistent on all target nodes."""
    summary = "NFS fstab entry"
    try:
        context = load_runtime_context(host)
        storage_config = _load_storage_config(host)
        mounts = _effective_mounts(host, storage_config)
        if not mounts:
            return _skip(summary, "No NFS mounts configured in storage_config.yml")

        outcomes = {}
        for mount_item in mounts:
            mount_point = mount_item.get("mount_point", "")
            source = mount_item.get("source", "")
            if not mount_point or not source:
                continue
            rows = _target_rows(context, mount_item)
            for row in rows:
                cmd = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["mount_config_fstab_read"],
                )
                key = f"{row['HOSTNAME']}:{mount_point}"
                found = False
                for line in cmd.stdout.strip().split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    if source in stripped and mount_point in stripped:
                        found = True
                        break
                outcomes[key] = (
                    (True, "fstab entry present")
                    if found
                    else (False, "fstab entry missing")
                )

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("Mapped mounts", len(outcomes))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Missing fstab: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_mount_config_bind_mounts(host):
    """Verify NFS bind mount targets are active on all target nodes."""
    summary = "NFS bind mounts"
    try:
        context = load_runtime_context(host)
        storage_config = _load_storage_config(host)
        mounts = _effective_mounts(host, storage_config)
        if not mounts:
            return _skip(summary, "No NFS mounts configured in storage_config.yml")

        bind_mounts = [
            m for m in mounts
            if m.get("node_key") and m.get("node_mount_point")
        ]
        if not bind_mounts:
            return _skip(summary, "No NFS bind mounts configured")

        outcomes = {}
        for mount_item in bind_mounts:
            mount_point = mount_item.get("mount_point", "")
            node_mount_points = mount_item.get("node_mount_point", [])
            if isinstance(node_mount_points, str):
                node_mount_points = [node_mount_points]
            rows = _target_rows(context, mount_item)
            for row in rows:
                for target in node_mount_points:
                    cmd = remote_command(
                        host, row,
                        PXEBOOT_COMMANDS["mount_config_mountpoint_check"]
                        % target,
                    )
                    key = f"{row['HOSTNAME']}:{target}"
                    output = cmd.stdout.strip().upper()
                    if output == "MOUNTED":
                        outcomes[key] = (True, "bind mounted")
                    else:
                        outcomes[key] = (False, "bind not mounted")

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("Bind mount checks", len(outcomes))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Bind not mounted: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_mount_config_bind_fstab(host):
    """Verify NFS bind mount fstab entries are persistent on target nodes."""
    summary = "NFS bind fstab entries"
    try:
        context = load_runtime_context(host)
        storage_config = _load_storage_config(host)
        mounts = _effective_mounts(host, storage_config)
        if not mounts:
            return _skip(summary, "No NFS mounts configured in storage_config.yml")

        bind_mounts = [
            m for m in mounts
            if m.get("node_key") and m.get("node_mount_point")
        ]
        if not bind_mounts:
            return _skip(summary, "No NFS bind mounts configured")

        outcomes = {}
        for mount_item in bind_mounts:
            mount_point = mount_item.get("mount_point", "")
            node_mount_points = mount_item.get("node_mount_point", [])
            if isinstance(node_mount_points, str):
                node_mount_points = [node_mount_points]
            rows = _target_rows(context, mount_item)
            for row in rows:
                cmd = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["mount_config_fstab_read"],
                )
                fstab_content = cmd.stdout.strip()
                for target in node_mount_points:
                    key = f"{row['HOSTNAME']}:{target}"
                    found = any(
                        target in line and "bind" in line
                        for line in fstab_content.split("\n")
                        if not line.strip().startswith("#")
                    )
                    outcomes[key] = (
                        (True, "bind fstab present")
                        if found
                        else (False, "bind fstab missing")
                    )

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("Bind fstab checks", len(outcomes))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Missing bind fstab: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_mount_config_node_subdirectory(host):
    """Verify per-node subdirectory exists under NFS mount point."""
    summary = "NFS per-node subdirectory"
    try:
        context = load_runtime_context(host)
        storage_config = _load_storage_config(host)
        mounts = _effective_mounts(host, storage_config)
        if not mounts:
            return _skip(summary, "No NFS mounts configured in storage_config.yml")

        bind_mounts = [
            m for m in mounts
            if m.get("node_key") and m.get("node_mount_point")
        ]
        if not bind_mounts:
            return _skip(summary, "No NFS bind mounts with node_key configured")

        outcomes = {}
        for mount_item in bind_mounts:
            mount_point = mount_item.get("mount_point", "")
            node_key = mount_item.get("node_key", "local_hostname")
            rows = _target_rows(context, mount_item)
            for row in rows:
                cmd = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["mount_config_node_key_value"]
                    % node_key,
                )
                node_value = cmd.stdout.strip()
                if not node_value:
                    outcomes[f"{row['HOSTNAME']}:{mount_point}"] = (
                        False,
                        f"could not resolve node_key={node_key}",
                    )
                    continue
                subdir = f"{mount_point}/{node_value}"
                dir_cmd = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["mount_config_dir_exists"] % subdir,
                )
                key = f"{row['HOSTNAME']}:{subdir}"
                if dir_cmd.rc == 0 and "exists" in dir_cmd.stdout.strip().lower():
                    outcomes[key] = (True, f"{node_value} subdir exists")
                else:
                    outcomes[key] = (False, f"{node_value} subdir missing")

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("Subdirectory checks", len(outcomes))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Missing subdirs: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_mount_config_permissions(host):
    """Verify NFS mount permissions match storage_config.yml on nodes."""
    summary = "NFS mount permissions"
    try:
        context = load_runtime_context(host)
        storage_config = _load_storage_config(host)
        mounts = _effective_mounts(host, storage_config)
        if not mounts:
            return _skip(summary, "No NFS mounts configured in storage_config.yml")

        perm_mounts = [m for m in mounts if m.get("permissions")]
        if not perm_mounts:
            return _skip(summary, "No NFS mounts with permissions configured")

        outcomes = {}
        for mount_item in perm_mounts:
            mount_point = mount_item.get("mount_point", "")
            perms = mount_item.get("permissions", {})
            expected_owner = str(perms.get("owner", "root"))
            expected_group = str(perms.get("group", "root"))
            expected_mode = str(perms.get("mode", "0644"))
            rows = _target_rows(context, mount_item)
            for row in rows:
                cmd = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["mount_config_stat"] % mount_point,
                )
                key = f"{row['HOSTNAME']}:{mount_point}"
                output = cmd.stdout.strip()
                parts = output.split("|")
                if len(parts) >= 3:
                    actual_mode = parts[0]
                    actual_owner = parts[1]
                    actual_group = parts[2]
                    mode_ok = actual_mode.endswith(
                        expected_mode.lstrip("0") or "0"
                    )
                    owner_ok = actual_owner == expected_owner
                    group_ok = actual_group == expected_group
                    if mode_ok and owner_ok and group_ok:
                        outcomes[key] = (
                            True,
                            f"{actual_owner}:{actual_group} {actual_mode}",
                        )
                    else:
                        outcomes[key] = (
                            False,
                            f"expected {expected_owner}:{expected_group} "
                            f"{expected_mode}, got {actual_owner}:{actual_group} "
                            f"{actual_mode}",
                        )
                else:
                    outcomes[key] = (False, "stat output unreadable")

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("Permission checks", len(outcomes))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Permission mismatch: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_mount_config_fg_targeting(host):
    """Verify NFS mounts are present on target FGs and absent on others."""
    summary = "NFS functional-group targeting"
    try:
        context = load_runtime_context(host)
        storage_config = _load_storage_config(host)
        mounts = _effective_mounts(host, storage_config)
        if not mounts:
            return _skip(summary, "No NFS mounts configured in storage_config.yml")

        targeted_mounts = [
            m for m in mounts
            if (isinstance(m.get("functional_group_prefix"), list)
                and m["functional_group_prefix"])
            or (isinstance(m.get("groups"), list) and m["groups"])
        ]
        if not targeted_mounts:
            return _skip(
                summary, "No NFS mounts with targeting (prefix or groups)"
            )

        outcomes = {}
        for mount_item in targeted_mounts:
            mount_point = mount_item.get("mount_point", "")
            if not mount_point:
                continue

            target_rows = _target_rows(context, mount_item)
            for row in target_rows:
                cmd = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["mount_config_mountpoint_check"]
                    % mount_point,
                )
                key = f"{row['HOSTNAME']}:{mount_point}:target"
                output = cmd.stdout.strip().upper()
                if output == "MOUNTED":
                    outcomes[key] = (True, "correctly mounted")
                else:
                    outcomes[key] = (False, "target node missing mount")

            non_targets = _non_target_rows(context, mount_item)
            for row in non_targets[:3]:
                cmd = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["mount_config_mountpoint_check"]
                    % mount_point,
                )
                key = f"{row['HOSTNAME']}:{mount_point}:non-target"
                output = cmd.stdout.strip().upper()
                if output == "MOUNTED":
                    outcomes[key] = (False, "non-target has mount (should not)")
                else:
                    outcomes[key] = (True, "correctly absent")

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("Targeting checks", len(outcomes))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Targeting failed: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_mount_config_no_duplicate_fstab(host):
    """Verify no duplicate fstab entries for configured NFS mounts."""
    summary = "NFS fstab uniqueness"
    try:
        context = load_runtime_context(host)
        storage_config = _load_storage_config(host)
        mounts = _effective_mounts(host, storage_config)
        if not mounts:
            return _skip(summary, "No NFS mounts configured in storage_config.yml")

        outcomes = {}
        for mount_item in mounts:
            mount_point = mount_item.get("mount_point", "")
            if not mount_point:
                continue
            rows = _target_rows(context, mount_item)
            for row in rows:
                cmd = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["mount_config_fstab_read"],
                )
                key = f"{row['HOSTNAME']}:{mount_point}"
                count = 0
                for line in cmd.stdout.strip().split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("#") or not stripped:
                        continue
                    fields = stripped.split()
                    if len(fields) >= 2 and fields[1] == mount_point:
                        count += 1
                if count == 1:
                    outcomes[key] = (True, "single entry")
                elif count == 0:
                    outcomes[key] = (False, "no entry found")
                else:
                    outcomes[key] = (False, f"duplicate entries ({count})")

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("Fstab uniqueness checks", len(outcomes))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Fstab issues: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_mount_config_writable(host):
    """Verify all configured NFS mounts are writable on target nodes."""
    summary = "NFS mount writability"
    try:
        context = load_runtime_context(host)
        storage_config = _load_storage_config(host)
        mounts = _effective_mounts(host, storage_config)
        if not mounts:
            return _skip(summary, "No NFS mounts configured in storage_config.yml")

        outcomes = {}
        for mount_item in mounts:
            mount_point = mount_item.get("mount_point", "")
            if not mount_point:
                continue
            rows = _target_rows(context, mount_item)
            for row in rows:
                cmd = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["mount_config_write_test"] % mount_point,
                )
                key = f"{row['HOSTNAME']}:{mount_point}"
                output = cmd.stdout.strip().upper()
                if output == "WRITABLE":
                    outcomes[key] = (True, "writable")
                else:
                    outcomes[key] = (False, "not writable")

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("Writability checks", len(outcomes))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "Not writable: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def _normalize_nfs_source(source: str) -> str:
    """Normalize an NFS source for comparison.

    Strips trailing slashes from the export path so that
    ``10.0.0.1:/export/`` and ``10.0.0.1:/export`` compare equal.
    """
    if ":" in source:
        server, export = source.split(":", 1)
        return f"{server}:{export.rstrip('/')}"
    return source.rstrip("/")


def check_mount_config_oim_mount(host):
    """Verify NFS storage is mounted on the OIM when mount_on_oim is true.

    Checks:
    1. Mount point is active (mountpoint -q).
    2. The mounted source matches the configured source (full
       server + export comparison after normalization).
    3. A persistent /etc/fstab entry exists for the mount (the 2.3
       production role uses ``ansible.posix.mount state=mounted``
       which always creates an fstab entry).
    """
    summary = "OIM NFS mount"
    try:
        storage_config = _load_storage_config(host)
        mounts = _effective_mounts(host, storage_config)
        if not mounts:
            return _skip(summary, "No NFS mounts configured in storage_config.yml")

        oim_mounts = [
            m for m in mounts
            if m.get("mount_on_oim") is True
        ]
        if not oim_mounts:
            return _skip(summary, "No NFS mounts with mount_on_oim: true")

        from omnia_auto import run_on_host

        outcomes = {}
        for mount_item in oim_mounts:
            mount_point = mount_item.get("mount_point", "")
            source = mount_item.get("source", "")
            if not mount_point:
                continue
            key = f"OIM:{mount_point}"
            problems = []

            # --- 1. Active mount check ---
            mp_cmd = run_on_host(
                host,
                f"mountpoint -q {mount_point} && echo MOUNTED || echo NOT_MOUNTED",
            )
            is_mounted = (
                mp_cmd.stdout.strip().splitlines()[-1].strip().upper()
                == "MOUNTED"
            )
            if not is_mounted:
                outcomes[key] = (False, "not mounted on OIM")
                continue

            # --- 2. Source identity check (full server + export) ---
            src_cmd = run_on_host(
                host,
                f"findmnt -rn -o SOURCE {mount_point}",
            )
            actual_source = src_cmd.stdout.strip()
            if not actual_source:
                problems.append("mounted but findmnt returned no source")
            else:
                norm_expected = _normalize_nfs_source(source)
                norm_actual = _normalize_nfs_source(actual_source)
                if norm_actual != norm_expected:
                    problems.append(
                        f"source mismatch: expected={source}, "
                        f"actual={actual_source}"
                    )

            # --- 3. Persistent fstab entry check ---
            fstab_cmd = run_on_host(host, "cat /etc/fstab")
            fstab_found = False
            for line in fstab_cmd.stdout.strip().split("\n"):
                fstab_fields = line.split()
                if (
                    len(fstab_fields) >= 2
                    and not line.lstrip().startswith("#")
                    and fstab_fields[1] == mount_point
                ):
                    fstab_found = True
                    break
            if not fstab_found:
                problems.append(
                    f"no /etc/fstab entry for {mount_point}"
                )

            if problems:
                outcomes[key] = (False, "; ".join(problems))
            else:
                outcomes[key] = (True, f"mounted from {actual_source}")

        failed = [k for k, v in outcomes.items() if not v[0]]
        fields = [("OIM mount checks", len(outcomes))]
        for key, (ok, detail) in outcomes.items():
            fields.append((f"  {key}", f"{'✓' if ok else '✗'} {detail}"))

        return runtime_result(
            not failed,
            summary,
            fields,
            "OIM not mounted: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
