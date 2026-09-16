# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Live validation of user-provided additional cloud-init metadata."""

import posixpath

import pytest

from fvt.check.feature_helpers import (
    read_remote_text,
    read_remote_yaml,
    target_paths,
)


pytestmark = [
    pytest.mark.additional_cloud_init,
    pytest.mark.functional,
]

ALLOWED_SECTION_KEYS = {"write_files", "runcmd"}
PROHIBITED_KEYS = {"bootcmd", "network", "network-config", "packages"}


def _feature_config(host):
    paths = target_paths()
    orchestrator_config = read_remote_yaml(
        host, posixpath.join(paths["input"], "orchestrator_config.yml")
    )
    configured_path = orchestrator_config.get(
        "additional_cloud_init_config_file", ""
    )
    assert isinstance(configured_path, str), (
        "additional_cloud_init_config_file must be a string"
    )
    if not configured_path.strip():
        pytest.skip("Additional cloud-init is not enabled for this dataset")
    return paths, configured_path, read_remote_yaml(host, configured_path)


@pytest.mark.order(20)
def test_additional_cloud_init_input_contract(host):
    """ORCH_FVT_ADDITIONAL_CLOUD_INIT_V001: Configured additional cloud-init uses the safe schema."""
    _paths, _configured_path, data = _feature_config(host)
    assert set(data) <= {"common", "groups"}, (
        f"Unsupported top-level additional cloud-init keys: {set(data) - {'common', 'groups'}}"
    )
    for section_name, section in [("common", data.get("common", {}))]:
        assert isinstance(section, dict), f"{section_name} must be a mapping"
        assert set(section) <= ALLOWED_SECTION_KEYS
        assert not (set(section) & PROHIBITED_KEYS)
    groups = data.get("groups", {})
    assert isinstance(groups, dict), "groups must be a mapping"
    for group_name, section in groups.items():
        assert isinstance(group_name, str) and group_name.strip()
        assert isinstance(section, dict), f"groups.{group_name} must be a mapping"
        assert set(section) <= ALLOWED_SECTION_KEYS
        assert not (set(section) & PROHIBITED_KEYS)


@pytest.mark.order(21)
def test_additional_cloud_init_common_metadata_rendered(host):
    """ORCH_FVT_ADDITIONAL_CLOUD_INIT_V002: Common user cloud-init is rendered with safe merge rules."""
    paths, _configured_path, data = _feature_config(host)
    if not data.get("common"):
        pytest.skip("No common additional cloud-init section is configured")
    rendered_path = posixpath.join(
        paths["data"], "openchami", "workdir", "metadata-service",
        "ms-group-additional_metadata_svc.yaml",
    )
    rendered = read_remote_text(host, rendered_path)
    assert "#cloud-config" in rendered
    assert "settings: [append]" in rendered
    assert "settings: [no_replace, recurse_list]" in rendered


@pytest.mark.order(22)
def test_additional_cloud_init_group_metadata_rendered(host):
    """ORCH_FVT_ADDITIONAL_CLOUD_INIT_V003: Every per-functional-group payload is rendered and grouped."""
    paths, _configured_path, data = _feature_config(host)
    groups = data.get("groups", {})
    if not groups:
        pytest.skip("No per-group additional cloud-init section is configured")
    metadata_dir = posixpath.join(
        paths["data"], "openchami", "workdir", "metadata-service"
    )
    nodes_dir = posixpath.join(
        paths["data"], "openchami", "workdir", "nodes"
    )
    for group_name in groups:
        metadata = read_remote_text(
            host,
            posixpath.join(
                metadata_dir, f"ms-group-additional_metadata_svc_{group_name}.yaml"
            ),
        )
        membership = read_remote_text(
            host,
            posixpath.join(
                nodes_dir, f"groups-additional_metadata_svc_{group_name}.yml"
            ),
        )
        assert "#cloud-config" in metadata
        assert f"additional_metadata_svc_{group_name}" in membership


@pytest.mark.order(23)
def test_additional_cloud_init_config_is_copied_to_workdir(host):
    """ORCH_FVT_ADDITIONAL_CLOUD_INIT_V004: The exact configured file is staged in OpenCHAMI workdir."""
    paths, configured_path, _data = _feature_config(host)
    staged_path = posixpath.join(
        paths["data"], "openchami", "workdir", "metadata-service",
        "additional_metadata_svc.yml",
    )
    assert read_remote_text(host, staged_path) == read_remote_text(
        host, configured_path
    )
