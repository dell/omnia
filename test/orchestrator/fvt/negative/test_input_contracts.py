# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Isolated negative tests for Orchestrator input and runner contracts."""

import json
import importlib.util
import logging
from pathlib import Path

import ansible.module_utils
import pytest
import yaml

from library.vars.common_vars import SRC_ORCHESTRATOR_DIR


MODULE_UTILS = Path(SRC_ORCHESTRATOR_DIR) / "plugins" / "module_utils"
if str(MODULE_UTILS) not in ansible.module_utils.__path__:
    ansible.module_utils.__path__.insert(0, str(MODULE_UTILS))

from ansible.module_utils.orchestrator_validation.core import (  # noqa: E402
    validation_engine,
)
from ansible.module_utils.orchestrator_validation.validators import (  # noqa: E402
    orchestrator_config_validator,
)


pytestmark = pytest.mark.negative
LOGGER = logging.getLogger("orchestrator-negative-test")
SCHEMA_DIR = MODULE_UTILS / "orchestrator_validation" / "schema"


def _schema(name):
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _write_mapping(path, header, rows):
    path.write_text(
        ",".join(header) + "\n" + "\n".join(",".join(row) for row in rows) + "\n",
        encoding="utf-8",
    )


@pytest.mark.order(1)
def test_invalid_yaml_is_rejected():
    """ORCH_FVT_NEGATIVE_V001: Malformed YAML is rejected before automation starts."""
    with pytest.raises(yaml.YAMLError):
        yaml.safe_load("Networks: [unterminated")


@pytest.mark.order(2)
def test_invalid_orchestrator_schema_is_rejected():
    """ORCH_FVT_NEGATIVE_V002: Non-boolean DCGM configuration fails JSON Schema."""
    errors = validation_engine.schema(
        {"dcgm_enabled": "yes"},
        _schema("orchestrator_config.json"),
        "orchestrator_config.yml",
        LOGGER,
    )
    assert any("dcgm_enabled" in error for error in errors)


@pytest.mark.order(3)
def test_missing_networks_key_is_rejected():
    """ORCH_FVT_NEGATIVE_V003: Network input without Networks fails JSON Schema."""
    errors = validation_engine.schema(
        {}, _schema("network_spec.json"), "network_spec.yml", LOGGER
    )
    assert errors and any("Networks" in error for error in errors)


@pytest.mark.order(4)
def test_missing_additional_cloud_init_file_is_rejected(tmp_path):
    """ORCH_FVT_NEGATIVE_V004: Configured but missing cloud-init input fails L2 validation."""
    errors = []
    missing = tmp_path / "missing-cloud-init.yml"
    orchestrator_config_validator._validate_additional_cloud_init_config(  # pylint: disable=protected-access
        {"additional_cloud_init_config_file": str(missing)}, errors, LOGGER
    )
    assert len(errors) == 1 and str(missing) in errors[0]


@pytest.mark.order(5)
def test_pxe_mapping_missing_required_header_is_rejected(tmp_path):
    """ORCH_FVT_NEGATIVE_V005: PXE mapping without required columns fails validation."""
    mapping = tmp_path / "pxe_mapping_file.csv"
    _write_mapping(mapping, ["HOSTNAME", "ADMIN_IP"], [["node01", "192.0.2.10"]])
    errors = []
    orchestrator_config_validator._validate_pxe_mapping_file(  # pylint: disable=protected-access
        {"pxe_mapping_file_path": str(mapping)}, str(tmp_path), errors, LOGGER
    )
    assert errors and "missing required column" in errors[0].lower()


@pytest.mark.order(6)
def test_duplicate_pxe_identity_is_rejected(tmp_path):
    """ORCH_FVT_NEGATIVE_V006: Duplicate PXE service tags, hosts, or IPs fail validation."""
    headers = orchestrator_config_validator.REQUIRED_HEADERS
    row = ["os_x86_64", "group", "ABC123", "", "node01", "mac1", "192.0.2.10", "mac2", "192.0.2.20"]
    mapping = tmp_path / "pxe_mapping_file.csv"
    _write_mapping(mapping, headers, [row, row])
    errors = []
    orchestrator_config_validator._validate_pxe_mapping_file(  # pylint: disable=protected-access
        {"pxe_mapping_file_path": str(mapping)}, str(tmp_path), errors, LOGGER
    )
    assert any("duplicate" in error.lower() for error in errors)


@pytest.mark.order(7)
def test_invalid_pxe_admin_ip_is_rejected(tmp_path):
    """ORCH_FVT_NEGATIVE_V007: Invalid administrative addresses fail PXE validation."""
    headers = orchestrator_config_validator.REQUIRED_HEADERS
    row = ["os_x86_64", "group", "ABC123", "", "node01", "mac1", "999.2.3.4", "mac2", "192.0.2.20"]
    mapping = tmp_path / "pxe_mapping_file.csv"
    _write_mapping(mapping, headers, [row])
    errors = []
    orchestrator_config_validator._validate_pxe_mapping_file(  # pylint: disable=protected-access
        {"pxe_mapping_file_path": str(mapping)}, str(tmp_path), errors, LOGGER
    )
    assert any("999.2.3.4" in error for error in errors)


@pytest.mark.order(8)
def test_dynamic_range_outside_admin_subnet_is_rejected():
    """ORCH_FVT_NEGATIVE_V008: DHCP ranges outside their subnet fail L2 validation."""
    network_data = {
        "Networks": [{
            "admin_network": {
                "subnet": "192.0.2.0",
                "netmask_bits": "24",
                "primary_oim_admin_ip": "192.0.2.10",
                "router": "192.0.2.1",
                "dynamic_range": "198.51.100.10-198.51.100.20",
            }
        }]
    }
    errors = validation_engine.logic_network(network_data, LOGGER)
    assert errors and any("dynamic" in error.lower() for error in errors)


@pytest.mark.order(9)
def test_unsupported_language_is_rejected():
    """ORCH_FVT_NEGATIVE_V009: Unsupported provisioning locale fails L2 validation."""
    errors = []
    orchestrator_config_validator._validate_language(  # pylint: disable=protected-access
        {"language": "fr_FR.UTF-8"}, errors, LOGGER
    )
    assert errors and "fr_FR.UTF-8" in errors[0]


@pytest.mark.order(10)
def test_non_positive_lease_time_is_rejected():
    """ORCH_FVT_NEGATIVE_V010: Zero and negative DHCP lease times fail validation."""
    for value in (0, -1, "invalid"):
        errors = []
        orchestrator_config_validator._validate_default_lease_time(  # pylint: disable=protected-access
            {"default_lease_time": value}, errors, LOGGER
        )
        assert errors, value


@pytest.mark.order(11)
def test_invalid_kernel_override_is_rejected():
    """ORCH_FVT_NEGATIVE_V011: Malformed kernel-version overrides fail validation."""
    errors = []
    orchestrator_config_validator._validate_kernel_version_override(  # pylint: disable=protected-access
        {"kernel_version_override": "latest"}, errors, LOGGER
    )
    assert errors and "latest" in errors[0]


@pytest.mark.order(12)
def test_destructive_runner_command_without_opt_in_is_rejected():
    """ORCH_FVT_NEGATIVE_V012: Cleanup execution without destructive marker fails closed."""
    test_root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "orchestrator_test_runner", test_root / "_run.py"
    )
    assert spec and spec.loader
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    assert not runner._validate_destructive_opt_in(  # pylint: disable=protected-access
        ["fvt_orchestrator", "cleanup", "test"]
    )
    assert runner._validate_destructive_opt_in(  # pylint: disable=protected-access
        [
            "fvt_orchestrator", "cleanup", "test",
            "--marker", "destructive",
        ]
    )
