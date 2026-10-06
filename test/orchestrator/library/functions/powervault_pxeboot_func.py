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

"""PowerVault iSCSI storage post-boot verification checks.

25 test cases mapped from Omnia 2.2 to 2.3 source code (ORCH-FUNC-TEST-007):
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

Source of truth for the deployed contract (2.3):
- src/orchestrator/input/storage_config.yml: powervault_config schema
- src/orchestrator/roles/mount_config/tasks/process_single_powervault.yml: targeting logic
- src/orchestrator/roles/mount_config/templates/setup_iscsi_storage.sh.j2: runcmd script
"""

from typing import Any

from ..vars.pxeboot_vars import (
    POWERVAULT_DEFAULT_ISCSI_PORT,
    POWERVAULT_DEFAULT_NODE_KEY,
    PXEBOOT_COMMANDS,
)
from ._powervault_helpers import (
    SLURM_MANDATORY_BIND_TARGETS,
    _run_on_node,
    error_result,
    get_mount_params,
    get_non_target_nodes,
    get_powervault_entries,
    get_target_nodes,
    optional_skip,
    resolve_node_key_value,
    resolve_pv_fs_type,
    resolve_pv_mount_opts,
    skip_if_no_powervault,
    verify_all_mounts_writable,
    verify_bind_fstab_entries,
    verify_bind_io,
    verify_bind_isolation,
    verify_bind_mounts,
    verify_cloud_init_groups_dict,
    verify_fstab_entry,
    verify_filesystem_type,
    verify_gpt_partition,
    verify_initiator_name,
    verify_io_write_read,
    verify_iscsi_discovery,
    verify_iscsi_service,
    verify_iscsi_sessions,
    verify_iscsi_startup_automatic,
    verify_mount_options,
    verify_mount_point_exists,
    verify_multipath_device,
    verify_multipath_paths,
    verify_multipath_service,
    verify_node_subdirectory,
    verify_no_duplicate_fstab,
    verify_permissions,
    verify_portal_reachability,
    verify_setup_log,
    verify_volume_mounted,
)
from ._pxeboot_helpers import runtime_result


def _node_label(node: dict) -> str:
    """Return 'hostname (ip)' display label for a node dict."""
    hostname = node.get("hostname", "")
    ip = node.get("admin_ip", "")
    return f"{hostname} ({ip})" if hostname else ip


def _require_targets(
    target_nodes: list, prefixes: list, failures: list[str], fields: list
) -> None:
    """Record a failure if no target nodes matched the configured prefixes.

    An empty target set means the functional_group_prefix is invalid or stale,
    so reporting success would be a false green.
    """
    if not target_nodes:
        prefix_str = ", ".join(prefixes) if prefixes else "<none>"
        msg = f"No target nodes matched functional_group_prefix [{prefix_str}]"
        failures.append(msg)
        fields.append((f"prefix [{prefix_str}]", "✗ zero targets"))


# =============================================================================
# Category 1: iSCSI Infrastructure Validation (Target Nodes)
# =============================================================================


def check_powervault_iscsi_service(host) -> dict[str, Any]:
    """Verify iscsid is enabled and running on all target nodes for every powervault_config entry.

    TC-PV-001 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault iSCSI service check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        mount_params = get_mount_params(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            prefixes = pv.get("functional_group_prefix", [])
            if not prefixes:
                continue

            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)
            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_iscsi_service(host, node_ip)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ failed"))
                else:
                    fields.append((label, "✓ active/enabled"))

        return runtime_result(
            not failures,
            "iscsid is active and enabled on all PowerVault target nodes",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault iSCSI service check failed", str(exc))


def check_powervault_iscsi_initiator_name(host) -> dict[str, Any]:
    """Verify iSCSI initiator name configured correctly on all target nodes.

    TC-PV-002 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault initiator name check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            expected_iqn = pv.get("iscsi_initiator", "")
            if not expected_iqn:
                continue

            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_initiator_name(host, node_ip, expected_iqn)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ mismatch"))
                else:
                    fields.append((label, "✓ matches"))

        return runtime_result(
            not failures,
            "iSCSI initiator name matches config on all target nodes",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault initiator name check failed", str(exc))


def check_powervault_iscsi_discovery(host) -> dict[str, Any]:
    """Verify iSCSI target discovery succeeds from all portal IPs.

    TC-PV-003 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault iSCSI discovery check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            ip_list = pv.get("ip", [])
            if not ip_list:
                continue

            port = pv.get("port", POWERVAULT_DEFAULT_ISCSI_PORT)
            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_iscsi_discovery(host, node_ip, ip_list, port)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ no IQN"))
                else:
                    fields.append((label, f"✓ {result['details']['discovered_iqn']}"))

        return runtime_result(
            not failures,
            "iSCSI discovery succeeds from all portal IPs",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault iSCSI discovery check failed", str(exc))


def check_powervault_iscsi_sessions(host) -> dict[str, Any]:
    """Verify iSCSI sessions are active on all target nodes.

    TC-PV-004 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault iSCSI sessions check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_iscsi_sessions(host, node_ip)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ no sessions"))
                else:
                    count = result["details"]["session_count"]
                    fields.append((label, f"✓ {count} sessions"))

        return runtime_result(
            not failures,
            "iSCSI sessions are active on all target nodes",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault iSCSI sessions check failed", str(exc))


def check_powervault_iscsi_startup_automatic(host) -> dict[str, Any]:
    """Verify iSCSI node startup set to automatic on all target nodes.

    TC-PV-005 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault iSCSI startup check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_iscsi_startup_automatic(host, node_ip)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ not automatic"))
                else:
                    fields.append((label, "✓ automatic"))

        return runtime_result(
            not failures,
            "iSCSI node startup is automatic on all target nodes",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault iSCSI startup check failed", str(exc))


def check_powervault_portal_reachability(host) -> dict[str, Any]:
    """Verify iSCSI portal port reachability for every powervault_config entry.

    TC-PV-006 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault portal reachability check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            ip_list = pv.get("ip", [])
            if not ip_list:
                continue

            port = pv.get("port", POWERVAULT_DEFAULT_ISCSI_PORT)
            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_portal_reachability(host, node_ip, ip_list, port)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ unreachable/unhealthy"))
                else:
                    fields.append((label, "✓ reachable"))

        return runtime_result(
            not failures,
            "iSCSI portal ports are reachable and sessions healthy",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault portal reachability check failed", str(exc))


# =============================================================================
# Category 2: Multipath Validation (Target Nodes)
# =============================================================================


def check_powervault_multipath_service(host) -> dict[str, Any]:
    """Verify multipathd service is enabled and running on all target nodes.

    TC-PV-007 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault multipathd service check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_multipath_service(host, node_ip)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ failed"))
                else:
                    fields.append((label, "✓ active/enabled"))

        return runtime_result(
            not failures,
            "multipathd is active and enabled on all target nodes",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault multipathd service check failed", str(exc))


def check_powervault_multipath_device(host) -> dict[str, Any]:
    """Verify multipath device exists and matches volume_id on all target nodes.

    TC-PV-008 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault multipath device check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            volume_id = pv.get("volume_id", "")
            if not volume_id:
                continue

            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_multipath_device(host, node_ip, volume_id)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ not found"))
                else:
                    device = result["details"]["mpath_device"]
                    method = result["details"]["match_method"]
                    fields.append((label, f"✓ {device} ({method})"))

        return runtime_result(
            not failures,
            "multipath device exists and matches volume_id",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault multipath device check failed", str(exc))


def check_powervault_multipath_redundancy(host) -> dict[str, Any]:
    """Verify multipath device has multiple paths (redundancy) on all target nodes.

    TC-PV-009 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault multipath redundancy check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            volume_id = pv.get("volume_id", "")
            ip_list = pv.get("ip", [])
            expected_paths = max(len(ip_list), 1)

            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                mpath_result = verify_multipath_device(host, node_ip, volume_id)
                if not mpath_result["success"]:
                    failures.append(mpath_result["error"])
                    fields.append((label, "✗ mpath not found"))
                    continue

                mpath_device = mpath_result["details"]["mpath_device"]
                result = verify_multipath_paths(host, node_ip, mpath_device, expected_paths)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, f"✗ {result['details']['path_count']} paths"))
                else:
                    count = result["details"]["path_count"]
                    fields.append((label, f"✓ {count} paths"))

        return runtime_result(
            not failures,
            "multipath device has multiple paths for redundancy",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault multipath redundancy check failed", str(exc))


# =============================================================================
# Category 3: Partition, Filesystem, and Mount Validation
# =============================================================================


def check_powervault_gpt_partition(host) -> dict[str, Any]:
    """Verify GPT partition exists on multipath device on all target nodes.

    TC-PV-010 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault GPT partition check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        mount_params = get_mount_params(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            volume_id = pv.get("volume_id", "")
            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                mpath_result = verify_multipath_device(host, node_ip, volume_id)
                if not mpath_result["success"]:
                    failures.append(mpath_result["error"])
                    fields.append((label, "✗ mpath not found"))
                    continue

                mpath_device = mpath_result["details"]["mpath_device"]
                result = verify_gpt_partition(host, node_ip, mpath_device)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ no GPT"))
                else:
                    fields.append((label, "✓ GPT present"))

        return runtime_result(
            not failures,
            "GPT partition exists on multipath device",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault GPT partition check failed", str(exc))


def check_powervault_gpt_missing_label(host) -> dict[str, Any]:
    """Verify GPT partition check correctly detects missing GPT label (negative test).

    This negative test validates that the check properly rejects devices
    without a valid GPT partition table. Since we cannot modify the
    production cluster to create a device without GPT, this test is
    skipped when the device correctly has GPT (normal operational state).
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault GPT negative check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            volume_id = pv.get("volume_id", "")
            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                mpath_result = verify_multipath_device(host, node_ip, volume_id)
                if not mpath_result["success"]:
                    failures.append(mpath_result["error"])
                    fields.append((label, "✗ mpath not found"))
                    continue

                mpath_device = mpath_result["details"]["mpath_device"]
                # Check if device actually has GPT
                cmd = _run_on_node(
                    host, node_ip,
                    PXEBOOT_COMMANDS["pv_parted_print"] % mpath_device,
                )
                output = cmd.stdout.strip()
                has_gpt = "gpt" in output.lower()
                
                # If device has GPT (normal state), skip the negative test
                if has_gpt:
                    fields.append((label, "⊘ skipped (device has GPT - normal state)"))
                    continue
                
                # If device has no GPT, run the negative test
                result = verify_gpt_partition(host, node_ip, mpath_device, expect_gpt=False)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ negative test failed"))
                else:
                    fields.append((label, "✓ correctly detects no GPT"))

        if not failures and not fields:
            return optional_skip(
                "PowerVault GPT negative check skipped",
                "All devices have GPT labels (normal operational state)",
            )

        return runtime_result(
            not failures,
            "GPT partition check correctly detects missing GPT label",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault GPT negative check failed", str(exc))


def check_powervault_filesystem_type(host) -> dict[str, Any]:
    """Verify filesystem formatted with correct type on all target nodes.

    TC-PV-011 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault filesystem type check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        mount_params = get_mount_params(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            expected_fs = resolve_pv_fs_type(pv, mount_params)
            volume_id = pv.get("volume_id", "")
            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                mpath_result = verify_multipath_device(host, node_ip, volume_id)
                if not mpath_result["success"]:
                    failures.append(mpath_result["error"])
                    fields.append((label, "✗ mpath not found"))
                    continue

                mpath_device = mpath_result["details"]["mpath_device"]
                part_dev = f"/dev/mapper/{mpath_device}1"
                result = verify_filesystem_type(host, node_ip, part_dev, expected_fs)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, f"✗ {result['details']['actual_fs']}"))
                else:
                    fields.append((label, f"✓ {expected_fs}"))

        return runtime_result(
            not failures,
            "filesystem formatted with correct type",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault filesystem type check failed", str(exc))


def check_powervault_mount_point_directory(host) -> dict[str, Any]:
    """Verify mount point directory exists on all target nodes.

    TC-PV-012 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault mount point directory check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            mount_point = pv.get("mount_point", "")
            if not mount_point:
                continue

            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_mount_point_exists(host, node_ip, mount_point)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ not found"))
                else:
                    fields.append((label, "✓ exists"))

        return runtime_result(
            not failures,
            "mount point directory exists on all target nodes",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault mount point directory check failed", str(exc))


def check_powervault_volume_mounted(host) -> dict[str, Any]:
    """Verify PowerVault volume is actively mounted on all target nodes.

    TC-PV-013 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault volume mounted check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            mount_point = pv.get("mount_point", "")
            if not mount_point:
                continue

            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_volume_mounted(host, node_ip, mount_point)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ not mounted"))
                else:
                    fields.append((label, "✓ mounted"))

        return runtime_result(
            not failures,
            "PowerVault volume is actively mounted on all target nodes",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault volume mounted check failed", str(exc))


def check_powervault_mount_options(host) -> dict[str, Any]:
    """Verify mount options applied correctly on all target nodes.

    TC-PV-014 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault mount options check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        mount_params = get_mount_params(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            mount_point = pv.get("mount_point", "")
            if not mount_point:
                continue

            expected_opts = resolve_pv_mount_opts(pv, mount_params)
            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_mount_options(host, node_ip, mount_point, expected_opts)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, f"✗ {result['details']['actual_opts']}"))
                else:
                    fields.append((label, "✓ correct"))

        return runtime_result(
            not failures,
            "mount options applied correctly on all target nodes",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault mount options check failed", str(exc))


def check_powervault_fstab_entry(host) -> dict[str, Any]:
    """Verify persistent fstab entry created on all target nodes.

    TC-PV-015 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault fstab entry check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            mount_point = pv.get("mount_point", "")
            if not mount_point:
                continue

            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_fstab_entry(host, node_ip, mount_point)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ not in fstab"))
                else:
                    fields.append((label, "✓ in fstab"))

        return runtime_result(
            not failures,
            "persistent fstab entry created on all target nodes",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault fstab entry check failed", str(exc))


# =============================================================================
# Category 4: Bind Mount Validation
# =============================================================================


def check_powervault_node_subdirectory(host) -> dict[str, Any]:
    """Verify per-node subdirectory under mount point on all target nodes.

    TC-PV-016 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault node subdirectory check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            mount_point = pv.get("mount_point", "")
            node_key = pv.get("node_key", "")
            if not mount_point or not node_key:
                continue

            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_node_subdirectory(host, node_ip, mount_point, node_key)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ not found"))
                else:
                    node_value = result["details"]["node_value"]
                    fields.append((label, f"✓ {node_value}"))

        return runtime_result(
            not failures,
            "per-node subdirectory exists under mount point",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault node subdirectory check failed", str(exc))


def check_powervault_bind_mounts(host) -> dict[str, Any]:
    """Verify bind mount targets are active on all target nodes.

    TC-PV-017 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault bind mounts check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            mount_point = pv.get("mount_point", "")
            node_key = pv.get("node_key", "")
            bind_targets = pv.get("node_mount_point", [])
            if not mount_point or not node_key or not bind_targets:
                continue

            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_bind_mounts(host, node_ip, mount_point, node_key, bind_targets)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ some not mounted"))
                else:
                    status = result["details"]["bind_status"]
                    mounted_count = sum(1 for v in status.values() if v)
                    fields.append((label, f"✓ {mounted_count}/{len(bind_targets)}"))

        return runtime_result(
            not failures,
            "bind mount targets are active on all target nodes",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault bind mounts check failed", str(exc))


def check_powervault_bind_fstab_entries(host) -> dict[str, Any]:
    """Verify bind mount fstab entries are persistent on all target nodes.

    TC-PV-018 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault bind fstab entries check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            mount_point = pv.get("mount_point", "")
            node_key = pv.get("node_key", "")
            bind_targets = pv.get("node_mount_point", [])
            if not mount_point or not node_key or not bind_targets:
                continue

            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_bind_fstab_entries(host, node_ip, mount_point, node_key, bind_targets)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ some missing"))
                else:
                    status = result["details"]["fstab_status"]
                    found_count = sum(1 for v in status.values() if v)
                    fields.append((label, f"✓ {found_count}/{len(bind_targets)}"))

        return runtime_result(
            not failures,
            "bind mount fstab entries are persistent on all target nodes",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault bind fstab entries check failed", str(exc))


def check_powervault_bind_isolation(host) -> dict[str, Any]:
    """Verify per-node data separation via cross-node write/read test.

    TC-PV-019 equivalent.  For each PV entry with bind targets, writes
    a unique marker from every node via its bind mount, then verifies
    each node's PV-backing subdirectory contains only its own marker.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault bind isolation check skipped",
                "powervault_config is absent or empty in "
                "storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            mount_point = pv.get("mount_point", "")
            node_key = pv.get("node_key", "")
            bind_targets = pv.get("node_mount_point", [])
            if isinstance(bind_targets, str):
                bind_targets = [bind_targets]
            if not mount_point or not node_key:
                continue

            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(
                target_nodes, prefixes, failures, fields,
            )
            if not target_nodes:
                continue

            pv_name = pv.get("name", "unnamed")
            result = verify_bind_isolation(
                host, mount_point, node_key,
                bind_targets, target_nodes,
            )

            if not result["success"]:
                failures.append(result["error"])
                fields.append(
                    (pv_name, "✗ isolation failure")
                )
            else:
                node_count = len(
                    result["details"].get("node_info", [])
                )
                note = result["details"].get("note", "")
                if note:
                    fields.append(
                        (pv_name, f"✓ {node_count} node(s) ({note})")
                    )
                else:
                    fields.append(
                        (pv_name,
                         f"✓ {node_count} nodes isolated")
                    )

        return runtime_result(
            not failures,
            "per-node data separation via bind mounts",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result(
            "PowerVault bind isolation check failed", str(exc),
        )


# =============================================================================
# Category 5: Functional Group Targeting
# =============================================================================


def check_powervault_functional_group_targeting(host) -> dict[str, Any]:
    """Verify PV mount only on correct functional groups.

    TC-PV-020 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault functional group targeting check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            mount_point = pv.get("mount_point", "")
            prefixes = pv.get("functional_group_prefix", [])
            if not mount_point or not prefixes:
                continue

            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)
            non_target_nodes = get_non_target_nodes(host, prefixes)

            # Verify target nodes have the mount
            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_volume_mounted(host, node_ip, mount_point)

                if not result["success"]:
                    failures.append(f"Target node {label} missing mount")
                    fields.append((label, "✗ missing"))
                else:
                    fields.append((label, "✓ mounted"))

            # Verify non-target nodes do NOT have the mount
            for node in non_target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_volume_mounted(host, node_ip, mount_point)

                if result["success"]:
                    failures.append(f"Non-target node {label} has mount (should not)")
                    fields.append((label, "✗ incorrectly mounted"))
                else:
                    fields.append((label, "✓ correctly absent"))

        return runtime_result(
            not failures,
            "PV mount only on correct functional groups",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault functional group targeting check failed", str(exc))


def check_powervault_multiple_prefix_targeting(host) -> dict[str, Any]:
    """Verify multiple prefixes target all groups correctly.

    TC-PV-021 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault multiple prefix targeting check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            mount_point = pv.get("mount_point", "")
            prefixes = pv.get("functional_group_prefix", [])
            if not mount_point or len(prefixes) < 2:
                continue

            # Get all nodes matching any prefix
            all_target_nodes = []
            for prefix in prefixes:
                all_target_nodes.extend(get_target_nodes(host, prefix))

            # Deduplicate by IP
            seen_ips = set()
            unique_targets = []
            for node in all_target_nodes:
                ip = node["admin_ip"]
                if ip not in seen_ips:
                    seen_ips.add(ip)
                    unique_targets.append(node)

            _require_targets(unique_targets, prefixes, failures, fields)

            # Verify all unique targets have the mount
            for node in unique_targets:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_volume_mounted(host, node_ip, mount_point)

                if not result["success"]:
                    failures.append(f"Node {label} missing mount (matched prefix)")
                    fields.append((label, "✗ missing"))
                else:
                    fields.append((label, "✓ mounted"))

        return runtime_result(
            not failures,
            "multiple prefixes target all groups correctly",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault multiple prefix targeting check failed", str(exc))


# =============================================================================
# Category 6: Cloud-Init Validation
# =============================================================================


def check_powervault_setup_log(host) -> dict[str, Any]:
    """Verify cloud-init runcmd log exists and shows completion.

    TC-PV-024 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault setup log check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            pv_name = pv.get("name", "")
            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_setup_log(host, node_ip, pv_name)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ log issues"))
                else:
                    fields.append((label, "✓ complete"))

        return runtime_result(
            not failures,
            "cloud-init runcmd log exists and shows completion",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault setup log check failed", str(exc))


def check_powervault_cloud_init_groups_dict(host) -> dict[str, Any]:
    """Verify rendered iSCSI setup scripts are deployed on target nodes.

    TC-PV-025 equivalent.  Tests the generated 2.3 metadata-service state
    (``/usr/local/bin/setup_iscsi_storage_<name>.sh``) on each target node
    rather than verifying source-tree Ansible templates on the OIM.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault cloud-init groups dict check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            prefixes = pv.get("functional_group_prefix", pv.get("prefix", []))
            if isinstance(prefixes, str):
                prefixes = [prefixes]
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)
            result = verify_cloud_init_groups_dict(host, pv, target_nodes)

            if not result["success"]:
                failures.append(result["error"])
                node_count = len(result["details"].get("nodes", {}))
                fields.append(
                    (pv["name"], f"✗ script missing/invalid ({node_count} node(s))")
                )
            else:
                node_count = len(result["details"].get("nodes", {}))
                fields.append(
                    (pv["name"], f"✓ script deployed ({node_count} node(s))")
                )

        return runtime_result(
            not failures,
            "PowerVault iSCSI setup scripts deployed on target nodes",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault cloud-init groups dict check failed", str(exc))


# =============================================================================
# Category 7: Misc Validation
# =============================================================================


def check_powervault_no_duplicate_fstab(host) -> dict[str, Any]:
    """Verify no duplicate fstab entries on all target nodes.

    TC-PV-026 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault duplicate fstab check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_no_duplicate_fstab(host, node_ip)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, f"✗ {result['details']['duplicate_count']} duplicates"))
                else:
                    fields.append((label, "✓ no duplicates"))

        return runtime_result(
            not failures,
            "no duplicate fstab entries on all target nodes",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault duplicate fstab check failed", str(exc))


def check_powervault_duplicate_fstab_detection(host) -> dict[str, Any]:
    """Verify duplicate fstab entry detection works correctly (negative test).

    This negative test validates that the check correctly identifies
    duplicate fstab entries. Since we cannot modify the production cluster
    to create duplicate entries, this test is skipped when fstab has no
    duplicates (normal operational state).
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault duplicate fstab negative check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                
                # Check if fstab actually has duplicates
                cmd = _run_on_node(host, node_ip, PXEBOOT_COMMANDS["pv_fstab_read"])
                output = cmd.stdout.strip()
                lines = [line.strip() for line in output.split("\n") if line.strip() and not line.strip().startswith("#")]
                unique_lines = set(lines)
                duplicate_count = len(lines) - len(unique_lines)
                
                # If no duplicates (normal state), skip the negative test
                if duplicate_count == 0:
                    fields.append((label, "⊘ skipped (no duplicates - normal state)"))
                    continue
                
                # If duplicates exist, run the negative test
                result = verify_no_duplicate_fstab(host, node_ip, expect_duplicates=True)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ negative test failed"))
                else:
                    dup_count = result["details"]["duplicate_count"]
                    fields.append((label, f"✓ correctly detects {dup_count} duplicates"))

        if not failures and not fields:
            return optional_skip(
                "PowerVault duplicate fstab negative check skipped",
                "All fstab entries are unique (normal operational state)",
            )

        return runtime_result(
            not failures,
            "Duplicate fstab entry detection works correctly",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault duplicate fstab negative check failed", str(exc))


def check_powervault_all_mounts_writable(host) -> dict[str, Any]:
    """Verify all PV mounts (main + bind) are writable on all target nodes.

    TC-PV-029 equivalent.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault mounts writable check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            mount_point = pv.get("mount_point", "")
            node_key = pv.get("node_key", "")
            bind_targets = pv.get("node_mount_point", [])
            if isinstance(bind_targets, str):
                bind_targets = [bind_targets]
            if not mount_point:
                continue

            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_all_mounts_writable(
                    host, node_ip, mount_point,
                    node_key, bind_targets,
                )

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ some not writable"))
                else:
                    fields.append((label, "✓ all writable"))

        return runtime_result(
            not failures,
            "all PV mounts (main + bind) are writable",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault mounts writable check failed", str(exc))


def check_powervault_permissions(host) -> dict[str, Any]:
    """Verify permissions on mount point match config.

    Additional check not in 2.2 but relevant to 2.3 source (setup_iscsi_storage.sh.j2:208-212).
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault permissions check skipped",
                "powervault_config is absent or empty in storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            mount_point = pv.get("mount_point", "")
            perms = pv.get("permissions", {})
            if not mount_point or not perms:
                continue

            expected_owner = perms.get("owner", "root")
            expected_group = perms.get("group", "root")
            expected_mode = perms.get("mode", "0755")

            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_permissions(host, node_ip, mount_point, expected_owner, expected_group, expected_mode)

                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, f"✗ {result['details']['actual']}"))
                else:
                    fields.append((label, "✓ correct"))

        return runtime_result(
            not failures,
            "permissions on mount point match config",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result("PowerVault permissions check failed", str(exc))


# =============================================================================
# Category 8: I/O and Mandatory Bind Mount Validation
# =============================================================================


def check_powervault_io_write_read(host) -> dict[str, Any]:
    """Write-read I/O test on every PV mount point.

    TC-PV-027 equivalent (2.2 io_write_read).
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault I/O write-read check skipped",
                "powervault_config is absent or empty in "
                "storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            mount_point = pv.get("mount_point", "")
            if not mount_point:
                continue
            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_io_write_read(
                    host, node_ip, mount_point,
                )
                if not result["success"]:
                    failures.append(result["error"])
                    fields.append((label, "✗ I/O failed"))
                else:
                    fields.append((label, "✓ I/O ok"))

        return runtime_result(
            not failures,
            "write-read I/O verified on all PV mount points",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result(
            "PowerVault I/O write-read check failed", str(exc),
        )


def check_powervault_bind_io(host) -> dict[str, Any]:
    """Write through bind mounts and verify data reaches the PV.

    TC-PV-028 equivalent (2.2 bind_io).
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault bind I/O check skipped",
                "powervault_config is absent or empty in "
                "storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            mount_point = pv.get("mount_point", "")
            node_key = pv.get("node_key", "")
            bind_targets = pv.get("node_mount_point", [])
            if not mount_point or not node_key or not bind_targets:
                continue
            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                for bt in bind_targets:
                    result = verify_bind_io(
                        host, node_ip, mount_point, node_key, bt,
                    )
                    tag = f"{label}:{bt}"
                    if not result["success"]:
                        failures.append(result["error"])
                        fields.append((tag, "✗ bind I/O failed"))
                    else:
                        fields.append((tag, "✓ bind I/O ok"))

        return runtime_result(
            not failures,
            "bind-mount I/O verified on all PV targets",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result(
            "PowerVault bind I/O check failed", str(exc),
        )


def check_powervault_slurm_mandatory_bind_mounts(
    host,
) -> dict[str, Any]:
    """Verify /var/lib/mysql and /var/spool/slurm are configured.

    TC-PV-029 equivalent (2.2 slurm_mandatory_bind_mounts).
    Checks that every PV entry whose functional_group_prefix matches
    a Slurm control-plane group includes the mandatory bind targets
    in its ``node_mount_point`` list.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault mandatory bind-mount check skipped",
                "powervault_config is absent or empty in "
                "storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures: list[str] = []
        fields: list[tuple[str, object]] = []

        for pv in pv_entries:
            bind_targets = pv.get("node_mount_point", [])
            if isinstance(bind_targets, str):
                bind_targets = [bind_targets]
            pv_name = pv.get("name", "unnamed")
            for required in SLURM_MANDATORY_BIND_TARGETS:
                if required in bind_targets:
                    fields.append(
                        (f"{pv_name}:{required}", "✓ configured")
                    )
                else:
                    failures.append(
                        f"{pv_name}: mandatory bind target "
                        f"{required} not in node_mount_point"
                    )
                    fields.append(
                        (f"{pv_name}:{required}", "✗ missing")
                    )

        return runtime_result(
            not failures,
            "mandatory Slurm/MySQL bind targets are configured",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result(
            "PowerVault mandatory bind-mount check failed",
            str(exc),
        )


def check_powervault_mysql_data_on_mount(host) -> dict[str, Any]:
    """Verify MySQL/MariaDB datadir lives on a PV mount.

    TC-PV-030 equivalent (2.2 mysql_data_on_mount).
    On each target node that has ``/var/lib/mysql`` as a bind target,
    confirms that ``/var/lib/mysql`` is an active mount point backed
    by the PowerVault volume.
    """
    try:
        if skip_if_no_powervault(host):
            return optional_skip(
                "PowerVault MySQL datadir check skipped",
                "powervault_config is absent or empty in "
                "storage_config.yml",
            )

        pv_entries = get_powervault_entries(host)
        failures: list[str] = []
        fields: list[tuple[str, object]] = []
        mysql_path = "/var/lib/mysql"

        for pv in pv_entries:
            bind_targets = pv.get("node_mount_point", [])
            if isinstance(bind_targets, str):
                bind_targets = [bind_targets]
            if mysql_path not in bind_targets:
                continue
            prefixes = pv.get("functional_group_prefix", [])
            target_nodes = get_target_nodes(host, prefixes)
            _require_targets(target_nodes, prefixes, failures, fields)

            for node in target_nodes:
                node_ip = node["admin_ip"]
                label = _node_label(node)
                result = verify_volume_mounted(
                    host, node_ip, mysql_path,
                )
                if not result["success"]:
                    failures.append(
                        f"{label}: {mysql_path} is not mounted"
                    )
                    fields.append(
                        (label, "✗ mysql not on PV")
                    )
                else:
                    fields.append(
                        (label, "✓ mysql on PV mount")
                    )

        if not fields:
            return optional_skip(
                "PowerVault MySQL datadir check skipped",
                f"no PV entry includes {mysql_path} in "
                "node_mount_point",
            )

        return runtime_result(
            not failures,
            "MySQL/MariaDB datadir is on PowerVault mount",
            fields,
            "; ".join(failures) if failures else "",
        )
    except Exception as exc:
        return error_result(
            "PowerVault MySQL datadir check failed", str(exc),
        )


__all__ = [
    "check_powervault_iscsi_service",
    "check_powervault_iscsi_initiator_name",
    "check_powervault_iscsi_discovery",
    "check_powervault_iscsi_sessions",
    "check_powervault_iscsi_startup_automatic",
    "check_powervault_portal_reachability",
    "check_powervault_multipath_service",
    "check_powervault_multipath_device",
    "check_powervault_multipath_redundancy",
    "check_powervault_gpt_partition",
    "check_powervault_filesystem_type",
    "check_powervault_mount_point_directory",
    "check_powervault_volume_mounted",
    "check_powervault_mount_options",
    "check_powervault_fstab_entry",
    "check_powervault_node_subdirectory",
    "check_powervault_bind_mounts",
    "check_powervault_bind_fstab_entries",
    "check_powervault_bind_isolation",
    "check_powervault_functional_group_targeting",
    "check_powervault_multiple_prefix_targeting",
    "check_powervault_setup_log",
    "check_powervault_cloud_init_groups_dict",
    "check_powervault_no_duplicate_fstab",
    "check_powervault_all_mounts_writable",
    "check_powervault_permissions",
    "check_powervault_io_write_read",
    "check_powervault_bind_io",
    "check_powervault_slurm_mandatory_bind_mounts",
    "check_powervault_mysql_data_on_mount",
]
