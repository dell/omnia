# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""Live verification of explicitly configured Slurm VAST storage."""

import shlex
import uuid

import pytest

from fvt.check.feature_helpers import (
    resolve_mount_profile,
    run_node_command,
    separate_vast_entries,
    storage_target_nodes,
)


pytestmark = [
    pytest.mark.storage,
    pytest.mark.vast,
    pytest.mark.functional,
]


def _configured_vast(host):
    entries, profiles = separate_vast_entries(host)
    if not entries:
        pytest.skip("No explicit slurm_cluster vast_storage_name is configured")
    return entries, profiles


def _targets(host, entry):
    targets = storage_target_nodes(host, entry)
    assert targets, f"VAST entry {entry['name']!r} resolves to no PXE nodes"
    return targets


def _mount_fields(result, label):
    assert result.rc == 0 and result.stdout.strip(), f"Mount is unavailable: {label}"
    fields = result.stdout.strip().split(None, 2)
    assert len(fields) == 3, f"Unexpected findmnt output for {label}: {result.stdout}"
    return fields


@pytest.mark.order(60)
def test_vast_mount_active_on_configured_targets(host):
    """ORCH_FVT_VAST_V001: Each configured VAST target has the expected active mount."""
    entries, profiles = _configured_vast(host)
    for entry in entries:
        expected = resolve_mount_profile(entry, profiles)
        mount_point = shlex.quote(entry["mount_point"])
        for name, address, _ in _targets(host, entry):
            result = run_node_command(
                host,
                address,
                f"findmnt -rn -T {mount_point} -o SOURCE,FSTYPE,OPTIONS",
            )
            source, fs_type, options = _mount_fields(result, f"{name}:{entry['mount_point']}")
            assert source == entry["source"], (
                f"VAST source mismatch on {name}: {source} != {entry['source']}"
            )
            expected_type = expected["fs_type"]
            if expected_type in {"nfs", "nfs4"}:
                assert fs_type in {"nfs", "nfs4"}
            elif expected_type != "auto":
                assert fs_type == expected_type
            active_options = set(options.split(","))
            required_options = {
                option
                for option in expected["mnt_opts"].split(",")
                if option and option not in {"defaults", "_netdev", "intr"}
            }
            assert required_options <= active_options, (
                f"Missing VAST mount options on {name}: "
                f"{sorted(required_options - active_options)}"
            )


@pytest.mark.order(61)
def test_vast_oim_mount_when_requested(host):
    """ORCH_FVT_VAST_V002: VAST entries marked mount_on_oim are active on the OIM."""
    entries, _ = _configured_vast(host)
    requested = [entry for entry in entries if entry.get("mount_on_oim") is True]
    if not requested:
        pytest.skip("No explicit VAST entry requests an OIM mount")
    for entry in requested:
        mount_point = shlex.quote(entry["mount_point"])
        result = host.run(
            f"findmnt -rn -T {mount_point} -o SOURCE,FSTYPE,OPTIONS"
        )
        source, fs_type, _ = _mount_fields(result, f"OIM:{entry['mount_point']}")
        assert source == entry["source"]
        assert fs_type in {"nfs", "nfs4"}


@pytest.mark.order(62)
def test_vast_slurm_bind_mounts_are_active(host):
    """ORCH_FVT_VAST_V003: Slurm data nodes expose VAST-backed application paths."""
    entries, _ = _configured_vast(host)
    checked = 0
    for entry in entries:
        for name, address, functional_group in _targets(host, entry):
            if not functional_group.startswith(("slurm_node", "login")):
                continue
            checked += 1
            for target in ("/hpc_tools", "/apps", "/scratch", "/projects"):
                result = run_node_command(
                    host,
                    address,
                    f"mountpoint -q {shlex.quote(target)}",
                )
                assert result.rc == 0, f"VAST bind mount {target} is absent on {name}"
    if not checked:
        pytest.skip("Configured VAST entries target no Slurm data nodes")


@pytest.mark.order(63)
def test_vast_fstab_and_permissions_match_configuration(host):
    """ORCH_FVT_VAST_V004: VAST persistence and configured permissions are correct."""
    entries, _ = _configured_vast(host)
    for entry in entries:
        quoted_source = shlex.quote(entry["source"])
        quoted_mount = shlex.quote(entry["mount_point"])
        permissions = entry.get("permissions") or {}
        for name, address, _ in _targets(host, entry):
            result = run_node_command(
                host,
                address,
                "awk -v src=" + quoted_source + " -v dst=" + quoted_mount + " "
                "'$1 == src && $2 == dst {count++} END {print count+0}' /etc/fstab",
            )
            assert result.rc == 0 and result.stdout.strip() == "1", (
                f"Expected one VAST fstab entry on {name}, got {result.stdout.strip()!r}"
            )
            if permissions:
                expected = "{}:{} {}".format(
                    permissions.get("owner", "root"),
                    permissions.get("group", "root"),
                    str(permissions.get("mode", "0755")).lstrip("0"),
                )
                result = run_node_command(
                    host,
                    address,
                    f"stat -c '%U:%G %a' {quoted_mount}",
                )
                assert result.rc == 0 and result.stdout.strip() == expected, (
                    f"VAST permissions mismatch on {name}: {result.stdout.strip()}"
                )


@pytest.mark.order(64)
def test_vast_rdma_client_when_configured(host):
    """ORCH_FVT_VAST_V005: RDMA VAST targets have compatible hardware and client state."""
    entries, profiles = _configured_vast(host)
    rdma_targets = []
    for entry in entries:
        resolved = resolve_mount_profile(entry, profiles)
        if "proto=rdma" in resolved["mnt_opts"].split(","):
            rdma_targets.extend((entry, target) for target in _targets(host, entry))
    if not rdma_targets:
        pytest.skip("No explicit VAST entry uses proto=rdma")
    for entry, (name, address, _) in rdma_targets:
        result = run_node_command(
            host,
            address,
            "lspci | grep -qi mellanox && rpm -q vastnfs >/dev/null && "
            "systemctl is-active --quiet rpcbind && lsmod | grep -q '^sunrpc' && "
            f"findmnt -rn -T {shlex.quote(entry['mount_point'])} -o OPTIONS "
            "| tr ',' '\\n' | grep -qx 'proto=rdma'",
        )
        assert result.rc == 0, f"VAST RDMA client is incomplete on {name}"


@pytest.mark.order(65)
@pytest.mark.destructive
def test_vast_shared_io_round_trip(host):
    """ORCH_FVT_VAST_V006: A reversible file round-trip is visible across VAST targets."""
    entries, _ = _configured_vast(host)
    entry = entries[0]
    targets = _targets(host, entry)
    token = f"omnia-storage-{uuid.uuid4().hex}"
    path = f"{entry['mount_point'].rstrip('/')}/.{token}"
    quoted_path = shlex.quote(path)
    writer_name, writer_address, _ = targets[0]
    try:
        result = run_node_command(
            host,
            writer_address,
            f"printf '%s' {shlex.quote(token)} > {quoted_path} && sync",
        )
        assert result.rc == 0, f"Unable to write VAST smoke file on {writer_name}"
        reader_name, reader_address, _ = targets[-1]
        result = run_node_command(host, reader_address, f"cat {quoted_path}")
        assert result.rc == 0 and result.stdout == token, (
            f"VAST smoke file was not shared correctly on {reader_name}"
        )
    finally:
        run_node_command(host, writer_address, f"rm -f -- {quoted_path}")
