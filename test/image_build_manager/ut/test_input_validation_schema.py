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
"""Unit tests for strict image-build input and repo-status schemas."""

# Pytest injects fixtures by reusing fixture function names as test arguments,
# and descriptive test names make per-test docstrings redundant.
# pylint: disable=missing-function-docstring,redefined-outer-name

import copy
import importlib.util
import json
import logging
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = (
    REPO_ROOT
    / "src/image_build_manager/plugins/module_utils/input_validation/schema"
)
ENGINE_PATH = (
    REPO_ROOT
    / "src/image_build_manager/plugins/module_utils/input_validation/core"
    / "validation_engine.py"
)
REPO_VALIDATOR_PATH = (
    REPO_ROOT
    / "src/image_build_manager/plugins/module_utils/input_validation/validators"
    / "repo_status_validator.py"
)


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


ENGINE = _load_module("image_build_validation_engine", ENGINE_PATH)
REPO_VALIDATOR = _load_module("repo_status_validator", REPO_VALIDATOR_PATH)
LOGGER = logging.getLogger(__name__)


def _schema(name):
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _validate(data, schema_name, label="input.yml"):
    errors = []
    ENGINE.schema(data, _schema(schema_name), label, errors, LOGGER)
    return errors


@pytest.fixture
def valid_config():
    """Return a complete valid config with genuine boolean values."""
    return {
        "repo_manager_output_path": "/opt/omnia/repo_manager/output/p/repo_status.yml",
        "s3_configurations": {"provider": "minio", "endpoint_url": ""},
        "image_build_type": "image-thrillhouse",
        "functional_groups_source": "config",
        "build_image": {
            "max_parallel": 0,
            "build_timeout": 7200,
            "force_rebuild": False,
            "backup_s3_images": False,
            "repo_ssl_verify": True,
        },
    }


def test_valid_boolean_values_pass(valid_config):
    assert not _validate(valid_config, "image_build_config.json")


@pytest.mark.parametrize(
    "field",
    [
        "repo_manager_output_path",
        "s3_configurations",
        "image_build_type",
        "functional_groups_source",
        "build_image",
    ],
)
def test_top_level_required_values_must_exist(valid_config, field):
    del valid_config[field]
    assert _validate(valid_config, "image_build_config.json")


@pytest.mark.parametrize(
    "field",
    ["force_rebuild", "backup_s3_images", "repo_ssl_verify"],
)
def test_quoted_boolean_values_fail(valid_config, field):
    config = copy.deepcopy(valid_config)
    config["build_image"][field] = "false"
    errors = _validate(config, "image_build_config.json")
    assert any("is not of type 'boolean'" in error for error in errors)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("repo_manager_output_path",), ""),
        (("image_build_type",), "   "),
        (("functional_groups_source",), None),
        (("s3_configurations", "provider"), ""),
    ],
)
def test_empty_scalar_values_fail(valid_config, path, value):
    config = copy.deepcopy(valid_config)
    target = config
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    errors = _validate(config, "image_build_config.json")
    assert errors


def test_optional_arm_host_may_be_empty(valid_config):
    valid_config["aarch64_inventory_host_ip"] = ""
    errors = _validate(valid_config, "image_build_config.json")
    assert not errors


def test_optional_arm_host_must_be_ipv4_when_set(valid_config):
    valid_config["aarch64_inventory_host_ip"] = "arm-builder.example.com"
    valid_config["aarch64_ssh_user"] = "root"
    errors = _validate(valid_config, "image_build_config.json")
    assert errors


def test_minio_requires_empty_endpoint(valid_config):
    valid_config["s3_configurations"]["endpoint_url"] = "http://192.0.2.1:9000"
    errors = _validate(valid_config, "image_build_config.json")
    assert any("endpoint_url" in error for error in errors)


def test_minio_endpoint_key_is_required(valid_config):
    del valid_config["s3_configurations"]["endpoint_url"]
    errors = _validate(valid_config, "image_build_config.json")
    assert any("endpoint_url" in error for error in errors)


def test_powerscale_requires_nonempty_endpoint(valid_config):
    valid_config["s3_configurations"] = {
        "provider": "powerscale",
        "endpoint_url": "",
    }
    errors = _validate(valid_config, "image_build_config.json")
    assert any("endpoint_url" in error for error in errors)


def test_powerscale_accepts_valid_endpoint(valid_config):
    valid_config["s3_configurations"] = {
        "provider": "powerscale",
        "endpoint_url": "https://powerscale.example.com:9021",
    }
    assert not _validate(valid_config, "image_build_config.json")


def test_arm_host_requires_nonempty_ssh_user(valid_config):
    valid_config["aarch64_inventory_host_ip"] = "192.0.2.20"
    valid_config["aarch64_ssh_user"] = ""
    assert _validate(valid_config, "image_build_config.json")


@pytest.mark.parametrize(
    "field",
    [
        "max_parallel",
        "build_timeout",
        "force_rebuild",
        "backup_s3_images",
        "repo_ssl_verify",
    ],
)
def test_all_build_controls_are_required(valid_config, field):
    del valid_config["build_image"][field]
    errors = _validate(valid_config, "image_build_config.json")
    assert any(field in error for error in errors)


def test_package_groups_schema_rejects_blank_package():
    data = {
        "os": "rhel",
        "os_version": "10.0",
        "base_packages": ["kernel", ""],
        "functional_groups": {"os_x86_64": {"packages": []}},
    }
    errors = _validate(data, "package_groups.json", "package_groups.yml")
    assert errors


@pytest.fixture
def valid_repo_status():
    return {
        "overall_status": "success",
        "cluster_os_type": "rhel",
        "repo_config": "partial",
        "repo_manager": {
            "port": 2225,
            "certificates": {
                "server_crt": "/opt/omnia/certs/server.crt",
                "server_key": "/opt/omnia/certs/server.key",
                "certs_dir": "/opt/omnia/certs",
            },
        },
        "repositories": {
            "10.0": {
                "x86_64": {
                    "baseos": {
                        "url": "https://192.0.2.10:2225/pulp/content/baseos/",
                        "priority": 100,
                    }
                },
                "aarch64": {},
            }
        },
        "file_repos": {"x86_64": {}, "aarch64": {}},
    }


def test_valid_repo_status_passes_schema_and_logic(valid_repo_status):
    assert not _validate(valid_repo_status, "repo_status.json", "repo_status.yml")
    assert not REPO_VALIDATOR.validate(valid_repo_status, LOGGER)


def test_repo_status_requires_success(valid_repo_status):
    valid_repo_status["overall_status"] = "failed"
    errors = _validate(valid_repo_status, "repo_status.json", "repo_status.yml")
    assert any("success" in error for error in errors)


def test_repo_status_requires_repo_manager_contract(valid_repo_status):
    del valid_repo_status["repo_manager"]
    errors = _validate(valid_repo_status, "repo_status.json", "repo_status.yml")
    assert any("repo_manager" in error for error in errors)


def test_repo_status_allows_empty_internet_repo_manager_values(valid_repo_status):
    valid_repo_status["repo_manager"] = {
        "port": "",
        "certificates": {
            "server_crt": "",
            "server_key": "",
            "certs_dir": "",
        },
    }
    assert not _validate(valid_repo_status, "repo_status.json", "repo_status.yml")


def test_repo_status_checks_repo_manager_structure_only(valid_repo_status):
    valid_repo_status["repo_manager"] = {
        "port": "",
        "certificates": {
            "server_crt": "/optional/ca.crt",
            "server_key": "",
            "certs_dir": "",
        },
    }
    assert not _validate(valid_repo_status, "repo_status.json", "repo_status.yml")


def test_repo_status_requires_certificate_structure(valid_repo_status):
    del valid_repo_status["repo_manager"]["certificates"]["server_key"]
    errors = _validate(valid_repo_status, "repo_status.json", "repo_status.yml")
    assert any("server_key" in error for error in errors)


@pytest.mark.parametrize("invalid_port", ["2225", 0, 65536, True, None])
def test_repo_status_rejects_invalid_port_type_or_range(
    valid_repo_status, invalid_port
):
    valid_repo_status["repo_manager"]["port"] = invalid_port
    assert _validate(valid_repo_status, "repo_status.json", "repo_status.yml")


def test_repo_status_requires_certificate_values_to_be_strings(valid_repo_status):
    valid_repo_status["repo_manager"]["certificates"]["server_crt"] = None
    errors = _validate(valid_repo_status, "repo_status.json", "repo_status.yml")
    assert any("server_crt" in error for error in errors)


def test_repo_status_rejects_blank_url(valid_repo_status):
    valid_repo_status["repositories"]["10.0"]["x86_64"]["baseos"]["url"] = ""
    errors = _validate(valid_repo_status, "repo_status.json", "repo_status.yml")
    assert errors


def test_repo_status_requires_usable_x86_repository(valid_repo_status):
    valid_repo_status["repositories"]["10.0"]["x86_64"] = {}
    assert REPO_VALIDATOR.validate(valid_repo_status, LOGGER)


def test_repo_status_boolean_priority_fails(valid_repo_status):
    valid_repo_status["repositories"]["10.0"]["x86_64"]["baseos"][
        "priority"
    ] = True
    errors = _validate(valid_repo_status, "repo_status.json", "repo_status.yml")
    assert any("is not of type 'integer'" in error for error in errors)


def test_internet_repo_status_sample_passes_contract():
    sample_path = (
        REPO_ROOT
        / "src/image_build_manager/samples/repo_manager_output/repo_status_internet.yml"
    )
    data = yaml.safe_load(sample_path.read_text(encoding="utf-8"))
    assert not _validate(data, "repo_status.json", "repo_status.yml")
    assert not REPO_VALIDATOR.validate(data, LOGGER)


def test_repo_contract_runs_in_build_setup_not_general_validation():
    image_root = REPO_ROOT / "src/image_build_manager"
    general_validator = (
        image_root / "plugins/modules/validate_image_build_config.py"
    ).read_text(encoding="utf-8")
    repo_loader = (
        image_root / "roles/image_build_setup/tasks/load_repo_status.yml"
    ).read_text(encoding="utf-8")
    setup_main = (
        image_root / "roles/image_build_setup/tasks/main.yml"
    ).read_text(encoding="utf-8")

    assert "repo_status.json" not in general_validator
    assert "validate_repo_status_contract:" in repo_loader
    assert "needs_repo_status | default(false) | bool" in setup_main
