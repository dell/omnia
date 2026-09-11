# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""Deterministic contracts for VAST and PowerVault storage wiring."""

import json

import pytest

from ut.source_loader import ORCHESTRATOR_ROOT


pytestmark = pytest.mark.unit


MOUNT_ROLE = ORCHESTRATOR_ROOT / "roles" / "mount_config"


def _read(path):
    return path.read_text(encoding="utf-8")


def test_powervault_schema_requires_storage_identity_and_targeting():
    """ORCH_UT_071: PowerVault requires portal, host, volume and target identity."""
    schema = json.loads(
        _read(
            ORCHESTRATOR_ROOT
            / "plugins/module_utils/orchestrator_validation/schema/storage_config.json"
        )
    )
    power_vault = schema["definitions"]["powerVault"]
    assert set(power_vault["required"]) == {
        "name",
        "ip",
        "iscsi_initiator",
        "volume_id",
        "mount_point",
        "functional_group_prefix",
    }
    assert "groups" not in power_vault["properties"]
    assert power_vault["dependencies"]["node_key"] == ["node_mount_point"]


def test_powervault_is_rendered_only_for_resolved_functional_groups():
    """ORCH_UT_072: PowerVault scripts are attached to resolved metadata groups."""
    task = _read(MOUNT_ROLE / "tasks/process_single_powervault.yml")
    assert "determine_target_groups.yml" in task
    assert "pv_rendered_script" in task
    assert "powervault_scripts" in task
    assert 'loop: "{{ mount_target_functional_groups }}"' in task


def test_powervault_setup_preserves_existing_filesystems_and_fstab():
    """ORCH_UT_073: PowerVault formatting and persistence are guarded for reruns."""
    script = _read(MOUNT_ROLE / "templates/setup_iscsi_storage.sh.j2")
    assert 'blkid -s TYPE -o value "${PART_DEV}"' in script
    assert 'Filesystem already exists on ${PART_DEV}; skipping format' in script
    assert 'if ! grep -qE "${FSTAB_MATCH}" /etc/fstab' in script
    assert 'grep -iF "${VOLUME_ID}"' in script


def test_mount_profiles_preserve_explicit_entry_precedence():
    """ORCH_UT_074: Explicit mount values override named profile defaults."""
    task = _read(MOUNT_ROLE / "tasks/process_single_mount.yml")
    for field in ("fs_type", "mnt_opts", "dump_freq", "fsck_pass"):
        assert f"mount_item.{field} | default(resolved_mount_profile.{field}" in task


def test_vast_reference_has_nfs_fallback_and_complete_validation():
    """ORCH_UT_075: Slurm VAST references resolve or reuse the selected NFS share."""
    task = _read(
        ORCHESTRATOR_ROOT
        / "roles/provision_common/tasks/configure_metadata_svc.yml"
    )
    assert "metadata_slurm_vast_storage_name" in task
    assert "metadata_slurm_nfs_storage_name" in task
    assert "metadata_slurm_vast_storage_matches | length == 1" in task
    assert "vast_mount_point" in task


def test_oim_vast_mount_falls_back_from_rdma_to_tcp():
    """ORCH_UT_076: OIM mounting never assumes an RDMA-capable controller."""
    task = _read(MOUNT_ROLE / "tasks/mount_on_oim.yml")
    assert "Fallback to tcp nfs if rdma" in task
    assert "default_client_mount_options" in task
    assert 'when: "\'rdma\' in mnt_opts"' in task


def test_vast_client_installation_is_hardware_aware():
    """ORCH_UT_077: VAST client setup detects Mellanox before installing."""
    script = _read(
        ORCHESTRATOR_ROOT
        / "roles/configure_ochami/templates/vast/configure_vast_installation.sh.j2"
    )
    assert "lspci | grep -i 'mellanox'" in script
    assert "dnf install -y --setopt=sslverify=0 vastnfs" in script
    assert "modprobe sunrpc" in script
    assert "systemctl start rpcbind" in script
