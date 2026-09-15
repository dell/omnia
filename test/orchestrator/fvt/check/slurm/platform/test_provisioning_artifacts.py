# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Live contracts shared by Slurm, Kubernetes, OS-only and custom nodes."""

from collections import Counter
import csv
from io import StringIO
import posixpath

import pytest

from fvt.check.feature_helpers import (
    read_remote_text,
    read_remote_yaml,
    target_paths,
)


pytestmark = pytest.mark.functional


def _mapping_rows(host):
    paths = target_paths()
    config = read_remote_yaml(
        host, posixpath.join(paths["input"], "orchestrator_config.yml")
    )
    mapping_path = config.get("pxe_mapping_file_path", "")
    if not isinstance(mapping_path, str) or not mapping_path.strip():
        mapping_path = posixpath.join(paths["input"], "pxe_mapping_file.csv")
    content = read_remote_text(host, mapping_path)
    clean_lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    rows = list(csv.DictReader(StringIO("\n".join(clean_lines))))
    assert rows, f"PXE mapping contains no nodes: {mapping_path}"
    return paths, rows


@pytest.mark.order(50)
def test_functional_group_artifact_covers_entire_mapping(host):
    """ORCH_FVT_PLATFORM_V001: Generated functional groups cover every PXE mapping group."""
    paths, rows = _mapping_rows(host)
    generated = read_remote_yaml(
        host,
        posixpath.join(
            paths["output"], ".data", "functional_groups_config.yml"
        ),
    )
    expected_groups = {row["GROUP_NAME"].strip() for row in rows}
    assert set(generated.get("groups", {})) == expected_groups
    functional_groups = generated.get("functional_groups")
    assert isinstance(functional_groups, list) and functional_groups
    assigned_groups = {
        group
        for entry in functional_groups
        for group in entry.get("group", [])
    }
    assert assigned_groups == expected_groups
    assert all(entry.get("name") for entry in functional_groups)
    assert all(entry.get("cluster_name") for entry in functional_groups)
    assert all(entry.get("category") for entry in functional_groups)
    assert all(entry.get("layer") in {"management", "compute"}
               for entry in functional_groups)


@pytest.mark.order(51)
def test_generated_inventory_preserves_node_identity(host):
    """ORCH_FVT_PLATFORM_V002: Inventory preserves every hostname, IP, BMC and service tag."""
    paths, rows = _mapping_rows(host)
    inventory = read_remote_yaml(
        host, posixpath.join(paths["output"], "orchestrator_inventory.yaml")
    )
    children = inventory.get("all", {}).get("children", {})
    assert isinstance(children, dict)
    actual_hosts = {
        hostname: values
        for child in children.values()
        for hostname, values in (child.get("hosts", {}) or {}).items()
        if hostname != "kube-vip"
    }
    expected_hosts = {row["HOSTNAME"].strip() for row in rows}
    assert set(actual_hosts) == expected_hosts
    for row in rows:
        values = actual_hosts[row["HOSTNAME"].strip()]
        assert str(values.get("ansible_host", "")) == row["ADMIN_IP"].strip()
        assert str(values.get("bmc_ip") or "") == row["BMC_IP"].strip()
        assert str(values.get("service_tag") or "") == row["SERVICE_TAG"].strip()
        assert str(values.get("group_name") or "") == row["GROUP_NAME"].strip()


@pytest.mark.order(52)
def test_bmc_inventory_covers_mapping_without_duplicates(host):
    """ORCH_FVT_PLATFORM_V003: Generated BMC inventory covers mapped BMC/group pairs once."""
    paths, rows = _mapping_rows(host)
    content = read_remote_text(
        host, posixpath.join(paths["output"], "bmc_group_data.csv")
    )
    actual_rows = list(csv.DictReader(StringIO(content)))
    expected = Counter(
        (row["BMC_IP"].strip(), row["GROUP_NAME"].strip()) for row in rows
    )
    actual = Counter(
        ((row.get("BMC_IP") or "").strip(), (row.get("GROUP_NAME") or "").strip())
        for row in actual_rows
    )
    for identity, count in expected.items():
        assert actual[identity] == count, (
            f"BMC inventory count mismatch for {identity}: "
            f"{actual[identity]} != {count}"
        )


@pytest.mark.order(53)
def test_provisioning_report_is_complete_and_successful(host):
    """ORCH_FVT_PLATFORM_V004: Provisioning report has consistent successful node/group counts."""
    paths, rows = _mapping_rows(host)
    report = read_remote_yaml(
        host, posixpath.join(paths["output"], "provisioning_report.yml")
    )
    total = len(rows)
    assert report.get("schema_version") == "1.0"
    assert report.get("phase") == "provisioning"
    assert int(report.get("total_expected_nodes", -1)) == total
    assert int(report.get("success_count", -1)) + int(
        report.get("failure_count", -1)
    ) == total
    assert report.get("overall_status") == "success", report.get(
        "missing_nodes"
    )
    assert report.get("missing_nodes") == []
    assert report.get("fg_missing_boot_config") == []
    assert report.get("fg_missing_metadata") == []


@pytest.mark.order(54)
def test_aggregate_status_preserves_all_node_results(host):
    """ORCH_FVT_PLATFORM_V005: Aggregate status keeps one coherent result per mapped node."""
    paths, rows = _mapping_rows(host)
    status = read_remote_yaml(
        host, posixpath.join(paths["output"], "orchestrator_status.yml")
    )
    total = len(rows)
    nodes = status.get("nodes")
    assert status.get("schema_version") == "1.0"
    assert int(status.get("total_nodes", -1)) == total
    assert isinstance(nodes, list) and len(nodes) == total
    identities = [node.get("service_tag") for node in nodes]
    assert len(set(identities)) == total
    assert set(identities) == {row["SERVICE_TAG"].strip() for row in rows}
    assert int(status.get("success_count", -1)) + int(
        status.get("failure_count", -1)
    ) == total
    assert status.get("overall_status") == "success"
