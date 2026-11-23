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

"""
Utils — Flexible Group Log Collection Unit Tests.

Test Case:
- TC_UT_utils_012: Unit tests for flexible functional group log collection
  validation, role-prefix routing, and address security in collect_pxe.yml.
"""

import importlib.util
import json
import sys
import types
from pathlib import Path
import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
VALIDATORS_DIR = (
    REPO_ROOT
    / "src"
    / "utils"
    / "plugins"
    / "module_utils"
    / "input_validation"
    / "validators"
)
SCHEMA_PATH = (
    REPO_ROOT
    / "src"
    / "utils"
    / "plugins"
    / "module_utils"
    / "input_validation"
    / "schema"
    / "collect_pxe_config.json"
)


def _load_validator():
    """Load collect_pxe_config_validator with mocked ansible dependencies."""
    module_path = VALIDATORS_DIR / "collect_pxe_config_validator.py"
    fake_msg_module = types.ModuleType("ansible.module_utils.input_validation.messages")

    class _FakeMessages:  # pylint: disable=too-few-public-methods
        pass

    fake_msg_module.utils_messages = _FakeMessages()
    for name, mod in [
        ("ansible", types.ModuleType("ansible")),
        ("ansible.module_utils", types.ModuleType("ansible.module_utils")),
        (
            "ansible.module_utils.input_validation",
            types.ModuleType("ansible.module_utils.input_validation"),
        ),
        ("ansible.module_utils.input_validation.messages", fake_msg_module),
    ]:
        sys.modules.setdefault(name, mod)

    spec = importlib.util.spec_from_file_location("collect_pxe_config_validator", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# pylint: disable=redefined-outer-name

@pytest.fixture(scope="module")
def validator():
    """Load and return the collect_pxe_config_validator module."""
    return _load_validator()


@pytest.fixture(scope="module")
def schema():
    """Load and return the collect_pxe_config JSON schema."""
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


class TestFlexibleGroupLogCollectionValidation:
    """TC_UT_utils_012: Flexible functional group collect_pxe validation unit tests."""

    @pytest.mark.parametrize(
        "group_name",
        [
            "fg_webserver_rhel_10_2_x86_64",
            "fg_database_rhel_10_2_x86_64",
            "fg_compute_worker_rhel_10_0_aarch64",
            "fg_ai_worker_rhel_10_2_aarch64",
            "fg_db_x86_64",
            "fg_analytics_aarch64",
        ],
    )
    def test_validator_accepts_valid_flexible_groups(self, validator, group_name):
        """FR-6.1: collect_pxe_config_validator accepts valid fg_ group names."""
        assert validator.is_valid_functional_group(group_name) is True
        errors = validator.validate({group_name: ["10.0.0.10"]})
        assert errors == []

    @pytest.mark.parametrize(
        ("group_name", "expected_role_prefix"),
        [
            ("fg_webserver_rhel_10_2_x86_64", "fg_webserver"),
            ("fg_database_rhel_10_2_x86_64", "fg_database"),
            ("fg_compute_worker_rhel_10_0_aarch64", "fg_compute_worker"),
            ("fg_db_x86_64", "fg_db"),
            ("slurm_node_rhel_10_0_aarch64", "slurm_node"),
            ("service_kube_node_rhel_10_0_x86_64", "service_kube_node"),
        ],
    )
    def test_role_prefix_extraction(self, validator, group_name, expected_role_prefix):
        """FR-6.1: Role prefix is cleanly extracted without per-group hardcoding."""
        role_prefix = validator.extract_role_prefix(group_name)
        assert role_prefix == expected_role_prefix

    @pytest.mark.parametrize(
        "invalid_group",
        [
            "webserver_rhel_10_2_x86_64",       # Missing fg_ prefix
            "custom_worker_x86_64",             # Non-predefined without fg_
            "fg_webserver_ppc64le",             # Unsupported architecture
            "fg_webserver_arm",                 # Unsupported architecture
            "fg_webserver",                     # Missing architecture
        ],
    )
    def test_validator_rejects_invalid_flexible_groups(self, validator, invalid_group):
        """FR-6.1: Invalid fg_ groups are rejected before collection."""
        assert validator.is_valid_functional_group(invalid_group) is False
        errors = validator.validate({invalid_group: ["10.0.0.10"]})
        assert len(errors) == 1
        assert invalid_group in errors[0]

    @pytest.mark.parametrize(
        "invalid_ip",
        [
            "127.0.0.1",
            "255.255.255.255",
            "not-an-ip",
            "999.999.999.999",
            "10.0.0",
        ],
    )
    def test_validator_rejects_unsafe_ip_addresses(self, validator, invalid_ip):
        """FR-6.1: Reserved and malformed IP addresses are rejected."""
        errors = validator.validate({"fg_webserver_rhel_10_2_x86_64": [invalid_ip]})
        assert len(errors) >= 1

    def test_schema_validates_flexible_groups(self, schema):
        """FR-6.1: collect_pxe_config.json schema accepts fg_ group keys and valid IPs."""
        valid_data = {
            "fg_webserver_rhel_10_2_x86_64": ["10.0.0.1", "10.0.0.2"],
            "fg_ai_worker_rhel_10_2_aarch64": ["10.0.1.1"],
            "slurm_node_rhel_10_0_x86_64": ["10.0.2.1"],
        }
        jsonschema.validate(instance=valid_data, schema=schema)

        # Invalid prefix should fail schema validation
        invalid_prefix_data = {"webserver_rhel_10_2_x86_64": ["10.0.0.1"]}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_prefix_data, schema=schema)

        # Invalid architecture should fail schema validation
        invalid_arch_data = {"fg_webserver_ppc64le": ["10.0.0.1"]}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_arch_data, schema=schema)

    def test_no_per_group_source_code_change_needed(self, validator):
        """AC-010, AC-016: Dynamic fg_<any_label> validates and routes without code edits."""
        dynamic_labels = ["gpu_cluster", "ml_inference", "storage_gateway", "dsp_worker"]
        for label in dynamic_labels:
            group_name = f"fg_{label}_rhel_10_2_x86_64"
            assert validator.is_valid_functional_group(group_name) is True
            assert validator.extract_role_prefix(group_name) == f"fg_{label}"
            errors = validator.validate({group_name: ["10.0.0.50"]})
            assert errors == []
