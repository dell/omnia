# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Shared helpers for live Orchestrator feature verification."""

import csv
from io import StringIO
from ipaddress import ip_address
import posixpath

import pytest
import yaml

from library.functions import load_test_config, run_ssh_command
from library.functions.slurm_func import (
    get_login_compiler_nodes,
    get_login_nodes,
    get_node_ip_from_pxe_mapping,
    get_slurm_compute_nodes,
    get_slurm_control_nodes,
)


def target_paths():
    """Return selected input, output, and Omnia data paths."""
    config = load_test_config()
    project = config.get("project_name", "project_default")
    shared_path = config.get("shared_path", "/opt/omnia/orchestrator")
    data_path = posixpath.dirname(shared_path.rstrip("/"))
    return {
        "input": posixpath.join(shared_path, "input", project),
        "output": posixpath.join(shared_path, "output", project),
        "data": data_path,
    }


def read_remote_text(host, path):
    """Read a required text file through testinfra on local or remote targets."""
    remote_file = host.file(path)
    assert remote_file.exists, f"Required target file is missing: {path}"
    return remote_file.content_string


def read_remote_yaml(host, path):
    """Load a required YAML mapping from the selected target."""
    content = read_remote_text(host, path)
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        pytest.fail(f"Invalid YAML in target file {path}: {exc}")
    assert isinstance(data, dict), f"Expected a YAML mapping in {path}"
    return data


def load_storage_inputs(host):
    """Return the active storage and Omnia configuration mappings."""
    paths = target_paths()
    storage = read_remote_yaml(
        host, posixpath.join(paths["input"], "storage_config.yml")
    )
    omnia = read_remote_yaml(
        host, posixpath.join(paths["input"], "omnia_config.yml")
    )
    return storage, omnia


def pxe_mapping_rows(host):
    """Return normalized rows from the active PXE mapping file."""
    paths = target_paths()
    orchestrator_config = read_remote_yaml(
        host, posixpath.join(paths["input"], "orchestrator_config.yml")
    )
    mapping_path = orchestrator_config.get("pxe_mapping_file_path", "")
    if not isinstance(mapping_path, str) or not mapping_path.strip():
        mapping_path = posixpath.join(paths["input"], "pxe_mapping_file.csv")
    content = read_remote_text(host, mapping_path)
    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    rows = list(csv.DictReader(StringIO("\n".join(lines))))
    assert rows, f"PXE mapping contains no nodes: {mapping_path}"
    return rows


def storage_target_nodes(host, entry):
    """Resolve one storage entry to unique hostname/administrative-IP pairs."""
    prefixes = entry.get("functional_group_prefix") or []
    groups = set(entry.get("groups") or [])
    targets = []
    missing = []
    for row in pxe_mapping_rows(host):
        functional_group = (row.get("FUNCTIONAL_GROUP_NAME") or "").strip()
        group = (row.get("GROUP_NAME") or "").strip()
        selected = (
            any(functional_group.startswith(prefix) for prefix in prefixes)
            if prefixes
            else group in groups
        )
        if not selected:
            continue
        name = (row.get("HOSTNAME") or "").strip()
        address = (row.get("ADMIN_IP") or "").strip()
        try:
            ip_address(address)
        except ValueError:
            missing.append(name or functional_group)
            continue
        targets.append((name, address, functional_group))
    assert not missing, f"Storage targets have no valid administrative IP: {missing}"
    return list(dict.fromkeys(targets))


def resolve_mount_profile(entry, profiles):
    """Resolve a mount profile while preserving entry-level precedence."""
    profile_name = entry.get("mount_params")
    profile = profiles.get(profile_name, {}) if profile_name else {}
    return {
        "fs_type": entry.get("fs_type", profile.get("fs_type", "auto")),
        "mnt_opts": entry.get("mnt_opts", profile.get("mnt_opts", "defaults")),
        "dump_freq": str(entry.get("dump_freq", profile.get("dump_freq", "0"))),
        "fsck_pass": str(entry.get("fsck_pass", profile.get("fsck_pass", "0"))),
    }


def separate_vast_entries(host):
    """Return explicit Slurm VAST references and their unique mount entries."""
    storage, omnia = load_storage_inputs(host)
    mounts = storage.get("mounts") or []
    names = {
        str(cluster.get("vast_storage_name") or "").strip()
        for cluster in omnia.get("slurm_cluster") or []
        if str(cluster.get("vast_storage_name") or "").strip()
    }
    resolved = []
    for name in sorted(names):
        matches = [entry for entry in mounts if entry.get("name") == name]
        assert len(matches) == 1, (
            f"VAST storage reference {name!r} resolved {len(matches)} times"
        )
        resolved.append(matches[0])
    return resolved, storage.get("mount_params") or {}


def powervault_entries(host):
    """Return configured PowerVault entries and mount profiles."""
    storage, _ = load_storage_inputs(host)
    return storage.get("powervault_config") or [], storage.get("mount_params") or {}


def slurm_node_ips(host, include_control=True):
    """Return validated administrative IPs for every configured Slurm node."""
    node_names = []
    if include_control:
        node_names.extend(get_slurm_control_nodes(host))
    node_names.extend(get_slurm_compute_nodes(host))
    node_names.extend(get_login_nodes(host))
    node_names.extend(get_login_compiler_nodes(host))

    resolved = []
    missing = []
    for name in dict.fromkeys(node_names):
        address = get_node_ip_from_pxe_mapping(host, name)
        if not address:
            missing.append(name)
            continue
        try:
            ip_address(address)
        except ValueError:
            missing.append(f"{name} (invalid IP: {address})")
            continue
        resolved.append((name, address))
    assert not missing, f"Slurm nodes have no valid administrative IP: {missing}"
    if not resolved:
        pytest.skip("No Slurm nodes are configured in pxe_mapping_file.csv")
    return resolved


def slurm_data_node_ips(host):
    """Return compute, login and login-compiler nodes, excluding control."""
    return slurm_node_ips(host, include_control=False)


def run_node_command(host, address, command, timeout=10):
    """Run a fixed verification command on a provisioned node through the OIM."""
    return run_ssh_command(
        host,
        address,
        command,
        connect_timeout=int(timeout),
    )
