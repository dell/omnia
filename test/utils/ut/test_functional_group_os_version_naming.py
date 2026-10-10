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
Regression tests for Utils hardcoding Omnia 2.3's OS/version-qualified
functional group names.

Omnia 2.3's orchestrator-generated ``pxe_mapping_file.csv`` names functional
groups as ``<role>_<os>_<version segments>_<arch>`` (e.g.
``slurm_node_rhel_10_0_aarch64``), and the real Ansible inventory groups
produced by ``generate_inventories`` use that exact, full name — not the
legacy bare ``<role>_<arch>`` form. Utils previously validated and parsed
``collect_pxe.yml`` against a fixed set of bare-arch-suffixed strings, so any
operator who populated it with real Omnia 2.3 group names (or any group name
using an OS version other than the ones hardcoded) would be rejected.

These tests pin the pattern-based fix in place: the OS name/version segment
must be optional and open-ended, mirroring the normalization regex already
used by orchestrator's ``generate_functional_groups`` module.
"""

# pylint: disable=missing-function-docstring,redefined-outer-name,too-few-public-methods

import importlib.util
import re
import sys
import types

import jinja2
import pytest
import yaml

from library.functions import utils_func
from library.vars.common_vars import FUNCTIONAL_GROUP_NAME_PATTERN

# Real-world group names taken directly from the sample pxe_mapping_file.csv
# (FUNCTIONAL_GROUP_NAME column) that surfaced this gap.
REAL_WORLD_VERSIONED_GROUPS = [
    "slurm_control_node_rhel_10_0_x86_64",
    "slurm_node_rhel_10_0_aarch64",
    "login_compiler_node_rhel_10_0_aarch64",
    "login_node_rhel_10_0_x86_64",
    "service_kube_control_plane_rhel_10_0_x86_64",
    "service_kube_node_rhel_10_0_x86_64",
]


def _load_validator_module(validators_dir):
    module_path = validators_dir / "collect_pxe_config_validator.py"
    fake_msg_module = types.ModuleType(
        "ansible.module_utils.input_validation.messages"
    )

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

    spec = importlib.util.spec_from_file_location(
        "collect_pxe_config_validator", module_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def validator_module(validators_dir):
    return _load_validator_module(validators_dir)


@pytest.mark.parametrize("group_name", REAL_WORLD_VERSIONED_GROUPS)
class TestValidatorAcceptsRealPxeMappingGroupNames:
    """The L2 validator must accept the real orchestrator-generated names."""

    def test_group_is_valid(self, validator_module, group_name):
        assert validator_module.is_valid_functional_group(group_name)

    def test_validate_reports_no_errors(self, validator_module, group_name):
        errors = validator_module.validate({group_name: ["10.0.0.1"]})
        assert errors == []


class TestValidatorHandlesNewAndUnknownOsVersions:
    """The OS name/version set is open-ended, not a fixed enumeration."""

    def test_future_rhel_point_release_is_accepted(self, validator_module):
        assert validator_module.is_valid_functional_group(
            "slurm_node_rhel_10_2_x86_64"
        )

    def test_future_ubuntu_release_is_accepted(self, validator_module):
        assert validator_module.is_valid_functional_group(
            "slurm_node_ubuntu_22_04_x86_64"
        )

    def test_primary_kube_control_plane_variant_is_accepted(self, validator_module):
        assert validator_module.is_valid_functional_group(
            "service_kube_control_plane_first_rhel_10_0_x86_64"
        )

    def test_legacy_bare_form_still_accepted(self, validator_module):
        assert validator_module.is_valid_functional_group("slurm_node_x86_64")

    def test_unsupported_role_still_rejected(self, validator_module):
        assert not validator_module.is_valid_functional_group("totally_bogus_group")

    def test_pxe_only_os_role_not_a_log_collection_role(self, validator_module):
        # "os_<os>_<version>_<arch>" is a PXE/provisioning-only functional
        # group (bare install image), not a Utils log-collection role.
        assert not validator_module.is_valid_functional_group("os_rhel_10_0_x86_64")


class TestAnsibleValidationRoleAcceptsVersionedNames:
    """validate_collect_config's Ansible-side pattern must match too."""

    @pytest.fixture
    def functional_group_pattern(self, src_dir):
        tasks_path = (
            src_dir / "roles" / "validate_collect_config" / "tasks" / "main.yml"
        )
        with open(tasks_path, encoding="utf-8") as handle:
            tasks = yaml.safe_load(handle)
        set_pattern_task = next(
            task
            for task in tasks
            if task.get("name") == "Set functional group name pattern"
        )
        pattern_str = set_pattern_task["ansible.builtin.set_fact"][
            "_functional_group_pattern"
        ].strip()
        return re.compile(pattern_str)

    @pytest.mark.parametrize("group_name", REAL_WORLD_VERSIONED_GROUPS)
    def test_pattern_matches_real_pxe_mapping_group_names(
        self, functional_group_pattern, group_name
    ):
        assert functional_group_pattern.match(group_name)

    def test_pattern_rejects_unsupported_role(self, functional_group_pattern):
        assert not functional_group_pattern.match("totally_bogus_group")


class TestPrepareTaskAggregatesAcrossOsVersions:
    """prepare.yml must combine multiple OS-version variants of one role+arch."""

    @pytest.fixture
    def pattern_vars(self, src_dir):
        vars_path = src_dir / "roles" / "log_collector" / "vars" / "main.yml"
        with open(vars_path, encoding="utf-8") as handle:
            return yaml.safe_load(handle)

    def _render_pattern(self, pattern_vars, key):
        env = jinja2.Environment()
        template = env.from_string(pattern_vars[key])
        return re.compile(
            template.render(_os_version_segment=pattern_vars["_os_version_segment"])
        )

    def test_slurm_nodes_arm_pattern_matches_multiple_os_versions(self, pattern_vars):
        pattern = self._render_pattern(pattern_vars, "slurm_nodes_arm_pattern")
        assert pattern.match("slurm_node_rhel_10_0_aarch64")
        assert pattern.match("slurm_node_rhel_10_1_aarch64")
        assert pattern.match("slurm_node_aarch64")  # legacy bare form
        assert not pattern.match("slurm_node_rhel_10_0_x86_64")  # wrong arch

    def test_k8s_masters_pattern_matches_primary_and_versioned(self, pattern_vars):
        pattern = self._render_pattern(pattern_vars, "k8s_masters_pattern")
        assert pattern.match("service_kube_control_plane_rhel_10_0_x86_64")
        assert pattern.match("service_kube_control_plane_first_rhel_10_0_x86_64")
        assert pattern.match("service_kube_control_plane_x86_64")

    def test_prepare_yml_aggregates_multiple_os_versions_of_same_bucket(
        self, src_dir
    ):
        """End-to-end: two OS-version variants of slurm_node/aarch64 both land
        in the same login_compiler/slurm aggregation bucket, not just the
        first one encountered."""
        vars_path = src_dir / "roles" / "log_collector" / "vars" / "main.yml"
        with open(vars_path, encoding="utf-8") as handle:
            pattern_vars = yaml.safe_load(handle)

        pattern = self._render_pattern(pattern_vars, "slurm_nodes_arm_pattern")

        collect_pxe_data = {
            "slurm_control_node_rhel_10_0_x86_64": ["172.16.107.52"],
            "slurm_node_rhel_10_0_aarch64": ["172.16.107.43", "172.16.107.44"],
            "slurm_node_rhel_10_1_aarch64": ["172.16.107.99"],
            "slurm_node_x86_64": ["10.0.0.1"],
        }
        matched_values = [
            value for key, value in collect_pxe_data.items() if pattern.match(key)
        ]
        aggregated = [ip for sublist in matched_values for ip in sublist]
        assert sorted(aggregated) == sorted(
            ["172.16.107.43", "172.16.107.44", "172.16.107.99"]
        )


class TestTestSideHelpersHandleVersionedNames:
    """Test-library helpers (FVT assertions) must not hardcode bare names either."""

    def test_functional_group_name_pattern_accepts_versioned_groups(self):
        for group_name in REAL_WORLD_VERSIONED_GROUPS:
            assert FUNCTIONAL_GROUP_NAME_PATTERN.match(group_name), group_name

    def test_validate_collect_pxe_file_accepts_versioned_groups(self, monkeypatch):
        # validate_collect_pxe_file delegates YAML loading to validate_yaml_file;
        # patch it directly so this test stays a pure unit test of the
        # group-name matching logic.
        monkeypatch.setattr(
            utils_func,
            "validate_yaml_file",
            lambda host, path: {
                "success": True,
                "data": {g: ["10.0.0.1"] for g in REAL_WORLD_VERSIONED_GROUPS},
                "error": "",
            },
        )
        result = utils_func.validate_collect_pxe_file(host=None, path="unused")
        assert result["success"], result["error"]
        assert sorted(result["groups"]) == sorted(REAL_WORLD_VERSIONED_GROUPS)
        assert not result["invalid_groups"]
