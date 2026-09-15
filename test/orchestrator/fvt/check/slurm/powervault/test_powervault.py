# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""Read-only live verification of configured PowerVault storage."""

import shlex
import uuid

import pytest

from fvt.check.feature_helpers import (
    powervault_entries,
    resolve_mount_profile,
    run_node_command,
    storage_target_nodes,
)


pytestmark = [
    pytest.mark.storage,
    pytest.mark.powervault,
    pytest.mark.functional,
]


def _configured_powervault(host):
    entries, profiles = powervault_entries(host)
    if not entries:
        pytest.skip("No powervault_config entries are configured")
    return entries, profiles


def _targets(host, entry):
    targets = storage_target_nodes(host, entry)
    assert targets, f"PowerVault entry {entry['name']!r} resolves to no PXE nodes"
    return targets


@pytest.mark.order(70)
def test_powervault_assets_and_prerequisites(host):
    """ORCH_FVT_POWERVAULT_V001: PowerVault targets contain their setup script and required tools."""
    entries, _ = _configured_powervault(host)
    tools = "iscsiadm multipath mpathconf parted kpartx blkid lsscsi"
    for entry in entries:
        script = f"/usr/local/bin/setup_iscsi_storage_{entry['name']}.sh"
        for name, address, _ in _targets(host, entry):
            result = run_node_command(
                host,
                address,
                f"test -x {shlex.quote(script)} && "
                f"for tool in {tools}; do command -v \"$tool\" >/dev/null || exit 1; done",
            )
            assert result.rc == 0, f"PowerVault prerequisites are incomplete on {name}"


@pytest.mark.order(71)
def test_powervault_services_and_initiator(host):
    """ORCH_FVT_POWERVAULT_V002: PowerVault targets have active services and the expected IQN."""
    entries, _ = _configured_powervault(host)
    for entry in entries:
        expected = f"InitiatorName={entry['iscsi_initiator']}"
        for name, address, _ in _targets(host, entry):
            result = run_node_command(
                host,
                address,
                "systemctl is-active --quiet iscsid && "
                "systemctl is-enabled --quiet iscsid && "
                "systemctl is-active --quiet multipathd && "
                f"grep -Fx -- {shlex.quote(expected)} /etc/iscsi/initiatorname.iscsi",
            )
            assert result.rc == 0, f"PowerVault service/IQN state is invalid on {name}"


@pytest.mark.order(72)
def test_powervault_sessions_and_exact_volume(host):
    """ORCH_FVT_POWERVAULT_V003: Every portal is logged in and the exact configured WWID is healthy."""
    entries, _ = _configured_powervault(host)
    for entry in entries:
        for name, address, _ in _targets(host, entry):
            sessions = run_node_command(host, address, "iscsiadm -m session")
            assert sessions.rc == 0, f"No PowerVault iSCSI session on {name}"
            for portal in entry["ip"]:
                assert portal in sessions.stdout, (
                    f"PowerVault portal {portal} has no session on {name}"
                )
            multipath = run_node_command(host, address, "multipath -ll")
            output = multipath.stdout.lower()
            assert multipath.rc == 0 and entry["volume_id"].lower() in output, (
                f"Configured PowerVault volume {entry['volume_id']} is absent on {name}"
            )
            assert "failed" not in output and "faulty" not in output, (
                f"Unhealthy PowerVault multipath state on {name}: {multipath.stdout}"
            )


@pytest.mark.order(73)
def test_powervault_mount_persistence_and_permissions(host):
    """ORCH_FVT_POWERVAULT_V004: PowerVault filesystems are mounted and persist as configured."""
    entries, profiles = _configured_powervault(host)
    for entry in entries:
        expected = resolve_mount_profile(entry, profiles)
        mount_point = shlex.quote(entry["mount_point"])
        permissions = entry.get("permissions") or {}
        for name, address, _ in _targets(host, entry):
            result = run_node_command(
                host,
                address,
                f"findmnt -rn -T {mount_point} -o SOURCE,FSTYPE,OPTIONS",
            )
            assert result.rc == 0 and result.stdout.strip(), (
                f"PowerVault mount {entry['mount_point']} is absent on {name}"
            )
            source, fs_type, _ = result.stdout.strip().split(None, 2)
            assert source.startswith("/dev/mapper/"), (
                f"Unexpected PowerVault device on {name}: {source}"
            )
            if expected["fs_type"] != "auto":
                assert fs_type == expected["fs_type"]
            count = run_node_command(
                host,
                address,
                f"awk -v dst={mount_point} "
                "'$2 == dst {count++} END {print count+0}' /etc/fstab",
            )
            assert count.rc == 0 and count.stdout.strip() == "1", (
                f"PowerVault fstab entry count is invalid on {name}: {count.stdout.strip()}"
            )
            if permissions:
                expected_mode = str(permissions.get("mode", "0755")).lstrip("0")
                expected_owner = permissions.get("owner", "root")
                expected_group = permissions.get("group", "root")
                stat_result = run_node_command(
                    host,
                    address,
                    f"stat -c '%U:%G %a' {mount_point}",
                )
                assert stat_result.rc == 0 and stat_result.stdout.strip() == (
                    f"{expected_owner}:{expected_group} {expected_mode}"
                )


@pytest.mark.order(74)
def test_powervault_node_bind_mounts(host):
    """ORCH_FVT_POWERVAULT_V005: Configured node-specific PowerVault bind mounts are active."""
    entries, _ = _configured_powervault(host)
    query_keys = {
        "local_hostname": "local_hostname",
        "local_ipv4": "ds.meta_data.instance_data.local_ipv4",
        "instance_id": "v1.instance_id",
    }
    applicable = [entry for entry in entries if entry.get("node_key")]
    if not applicable:
        pytest.skip("No PowerVault entry configures node-specific bind mounts")
    for entry in applicable:
        query_key = query_keys[entry["node_key"]]
        for name, address, _ in _targets(host, entry):
            node_value = run_node_command(
                host, address, f"cloud-init query {shlex.quote(query_key)}"
            )
            assert node_value.rc == 0 and node_value.stdout.strip()
            for target in entry.get("node_mount_point") or []:
                expected_source = (
                    f"{entry['mount_point'].rstrip('/')}/{node_value.stdout.strip()}"
                    f"{target}"
                )
                result = run_node_command(
                    host,
                    address,
                    f"mountpoint -q {shlex.quote(target)} && "
                    "grep -F -- "
                    f"{shlex.quote(expected_source + ' ' + target + ' none bind')} "
                    "/etc/fstab",
                )
                assert result.rc == 0, (
                    f"PowerVault bind mount {target} is invalid on {name}"
                )


@pytest.mark.order(75)
@pytest.mark.destructive
def test_powervault_io_round_trip(host):
    """ORCH_FVT_POWERVAULT_V006: A reversible PowerVault file write and read succeeds."""
    entries, _ = _configured_powervault(host)
    entry = entries[0]
    name, address, _ = _targets(host, entry)[0]
    token = f"omnia-storage-{uuid.uuid4().hex}"
    path = f"{entry['mount_point'].rstrip('/')}/.{token}"
    quoted_path = shlex.quote(path)
    try:
        result = run_node_command(
            host,
            address,
            f"printf '%s' {shlex.quote(token)} > {quoted_path} && sync && cat {quoted_path}",
        )
        assert result.rc == 0 and result.stdout == token, (
            f"PowerVault I/O smoke test failed on {name}"
        )
    finally:
        run_node_command(host, address, f"rm -f -- {quoted_path}")
