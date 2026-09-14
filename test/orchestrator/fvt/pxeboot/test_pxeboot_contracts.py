# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Strict credential, Redfish, and output contracts for the PXE lifecycle."""

import csv
from io import StringIO
from ipaddress import ip_address
import posixpath

import pytest
import yaml

from library.functions import load_test_config, run_on_host


pytestmark = pytest.mark.destructive


def _paths():
    config = load_test_config()
    shared = config.get("shared_path", "/opt/omnia/orchestrator").rstrip("/")
    project = config.get("project_name", "project_default")
    return (
        posixpath.join(shared, "input", project),
        posixpath.join(shared, "output", project),
    )


def _read(host, path):
    remote_file = host.file(path)
    assert remote_file.exists, f"Required target file is missing: {path}"
    return remote_file.content_string


def _yaml(host, path):
    try:
        data = yaml.safe_load(_read(host, path))
    except yaml.YAMLError as exc:
        pytest.fail(f"Invalid YAML in {path}: {exc}")
    assert isinstance(data, dict), f"Expected YAML mapping in {path}"
    return data


def _require_pxe_enabled(host):
    input_dir, _ = _paths()
    config = _yaml(host, posixpath.join(input_dir, "orchestrator_config.yml"))
    enabled = config.get("enable_pxe_boot", True)
    assert isinstance(enabled, bool), "enable_pxe_boot must be boolean"
    if not enabled:
        pytest.skip("PXE boot is disabled for this environment")


def _mapping(host):
    _require_pxe_enabled(host)
    input_dir, _ = _paths()
    content = _read(host, posixpath.join(input_dir, "pxe_mapping_file.csv"))
    rows = list(csv.DictReader(StringIO(content)))
    assert rows, "pxe_mapping_file.csv must contain at least one node"
    return rows


def _assert_count_contract(data, label):
    for key in ("total_nodes", "success_count", "failure_count"):
        assert key in data, f"{label} missing {key}"
        assert int(data[key]) >= 0, f"{label}.{key} must be non-negative"
    assert int(data["success_count"]) + int(data["failure_count"]) == int(
        data["total_nodes"]
    ), f"{label} counts are inconsistent"


@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(24)
def test_set_pxe_boot_config_exists_or_defaults_apply(host):
    """ORCH_FVT_PXEBOOT_V024: Optional PXE settings exist or defaults apply."""
    _require_pxe_enabled(host)
    input_dir, _ = _paths()
    custom = host.file(posixpath.join(input_dir, "set_pxe_boot_config.yml"))
    if not custom.exists:
        pytest.skip("Optional set_pxe_boot_config.yml is absent; defaults apply")
    assert custom.is_file and custom.size > 0


@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(25)
def test_bmc_credential_artifacts_exist(host):
    """ORCH_FVT_PXEBOOT_V025: Enabled PXE has encrypted credential artifacts."""
    _require_pxe_enabled(host)
    input_dir, _ = _paths()
    for filename in ("omnia_config_credentials.yml", ".omnia_config_credentials_key"):
        credential = host.file(posixpath.join(input_dir, filename))
        assert credential.is_file and credential.size > 0, filename


@pytest.mark.functional
@pytest.mark.order(26)
def test_bmc_credential_permissions(host):
    """ORCH_FVT_PXEBOOT_V026: BMC credentials are inaccessible to other users."""
    _require_pxe_enabled(host)
    input_dir, _ = _paths()
    for filename in ("omnia_config_credentials.yml", ".omnia_config_credentials_key"):
        credential = host.file(posixpath.join(input_dir, filename))
        assert credential.is_file, filename
        assert credential.mode & 0o077 == 0, (
            f"Unsafe mode {oct(credential.mode)} on {filename}"
        )


@pytest.mark.functional
@pytest.mark.order(27)
def test_idrac_redfish_endpoints_reachable(host):
    """ORCH_FVT_PXEBOOT_V027: Every mapped BMC exposes a Redfish endpoint."""
    failures = []
    for row in _mapping(host):
        address = str(ip_address(row["BMC_IP"].strip()))
        result = run_on_host(
            host,
            "curl -k -sS --connect-timeout 5 -o /dev/null "
            f"-w '%{{http_code}}' https://{address}/redfish/v1",
        )
        if result.rc != 0 or result.stdout.strip() == "000":
            failures.append(address)
    assert not failures, f"Unreachable iDRAC Redfish endpoints: {failures}"


@pytest.mark.sanity
@pytest.mark.buildstream
@pytest.mark.order(28)
def test_pxeboot_status_output_exists(host):
    """ORCH_FVT_PXEBOOT_V028: PXE execution writes pxeboot_status.yml."""
    _require_pxe_enabled(host)
    _, output_dir = _paths()
    assert host.file(posixpath.join(output_dir, "pxeboot_status.yml")).is_file


@pytest.mark.functional
@pytest.mark.order(29)
def test_pxeboot_status_output_format(host):
    """ORCH_FVT_PXEBOOT_V029: PXE status represents selected nodes consistently."""
    _require_pxe_enabled(host)
    _, output_dir = _paths()
    data = _yaml(host, posixpath.join(output_dir, "pxeboot_status.yml"))
    assert data.get("schema_version") == "1.0"
    assert data.get("phase") == "pxeboot"
    assert data.get("overall_status") in {"success", "failed"}
    assert isinstance(data.get("nodes"), list)
    _assert_count_contract(data, "pxeboot_status.yml")
    assert len(data["nodes"]) == int(data["total_nodes"])
    for node in data["nodes"]:
        assert {"bmc_ip", "admin_ip", "hostname", "status"} <= set(node)
        assert node["status"] in {"success", "failed"}
