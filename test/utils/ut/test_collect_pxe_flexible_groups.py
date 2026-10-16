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
ER-ORCH-009: Utils log collection must accept and route flexible functional
groups carrying the mandatory ``fg_`` prefix across the validator, the JSON
schema, the Ansible validation role, and the log_collector routing, without a
source change per new flexible group name.
"""

# pylint: disable=missing-function-docstring,redefined-outer-name

import importlib.util
import json
import re
import sys
import types

import pytest
import yaml

FLEXIBLE_GROUP = "fg_webserver_rhel_10_2_x86_64"
FLEXIBLE_GROUP_ARM = "fg_mpi_worker_rhel_10_0_aarch64"


def _load_validator_module(validators_dir):
    module_path = validators_dir / "collect_pxe_config_validator.py"
    assert module_path.exists(), f"validator module not found: {module_path}"

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


class TestValidatorAcceptsFlexibleGroups:
    @pytest.mark.parametrize("group", [FLEXIBLE_GROUP, FLEXIBLE_GROUP_ARM])
    def test_validate_accepts_flexible_group(self, validator_module, group):
        assert validator_module.is_valid_functional_group(group)
        assert validator_module.validate({group: ["192.168.1.55"]}) == []

    def test_validate_rejects_fg_without_architecture(self, validator_module):
        errors = validator_module.validate({"fg_webserver_rhel_10_2": ["192.168.1.55"]})
        assert len(errors) == 1
        assert "fg_webserver_rhel_10_2" in errors[0]

    def test_error_message_documents_fg_prefix(self, validator_module):
        errors = validator_module.validate({"not_a_real_group": ["192.168.1.55"]})
        assert len(errors) == 1
        assert "fg_" in errors[0]


class TestSchemaAcceptsFlexibleGroups:
    @pytest.mark.parametrize("group", [FLEXIBLE_GROUP, FLEXIBLE_GROUP_ARM])
    def test_schema_accepts_flexible_group(self, schema_dir, group):
        schema = json.loads(
            (schema_dir / "collect_pxe_config.json").read_text(encoding="utf-8")
        )
        patterns = list(schema["patternProperties"].keys())
        assert any(re.match(pattern, group) for pattern in patterns)


class TestValidateCollectConfigRoleAcceptsFlexibleGroups:
    def _functional_group_pattern(self, src_dir):
        tasks_path = (
            src_dir / "roles" / "validate_collect_config" / "tasks" / "main.yml"
        )
        tasks = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
        set_pattern_task = next(
            task
            for task in tasks
            if task.get("name") == "Set functional group name pattern"
        )
        pattern_str = set_pattern_task["ansible.builtin.set_fact"][
            "_functional_group_pattern"
        ].strip()
        return re.compile(pattern_str)

    @pytest.mark.parametrize("group", [FLEXIBLE_GROUP, FLEXIBLE_GROUP_ARM])
    def test_pattern_matches_flexible_group(self, src_dir, group):
        assert self._functional_group_pattern(src_dir).match(group)

    def test_error_message_documents_fg_prefix(self, src_dir):
        vars_path = src_dir / "roles" / "validate_collect_config" / "vars" / "main.yml"
        data = yaml.safe_load(vars_path.read_text(encoding="utf-8"))
        assert "fg_" in data["invalid_group_name_msg"]


class TestLogCollectorRoutesFlexibleGroups:
    def test_collect_playbook_has_flexible_play(self, src_dir):
        collect_path = src_dir / "playbooks" / "collect.yml"
        plays = yaml.safe_load(collect_path.read_text(encoding="utf-8"))
        flexible_play = next(
            (play for play in plays if play.get("hosts") == "flexible_nodes"), None
        )
        assert flexible_play is not None
        roles = flexible_play["roles"]
        assert any(role.get("stage") == "flexible" for role in roles)

    def test_role_vars_define_flexible_pattern(self, src_dir):
        vars_path = src_dir / "roles" / "log_collector" / "vars" / "main.yml"
        content = vars_path.read_text(encoding="utf-8")
        assert "flexible_nodes_pattern" in content
        assert "functional_group_config_file" in content

    def test_flexible_pattern_matches_flexible_group_names(self, src_dir):
        vars_path = src_dir / "roles" / "log_collector" / "vars" / "main.yml"
        data = yaml.safe_load(vars_path.read_text(encoding="utf-8"))
        # Resolve the nested Jinja reference to the shared os/version segment.
        pattern = data["flexible_nodes_pattern"].replace(
            "{{ _os_version_segment }}", data["_os_version_segment"]
        )
        compiled = re.compile(pattern)
        assert compiled.match(FLEXIBLE_GROUP)
        assert compiled.match(FLEXIBLE_GROUP_ARM)
        assert not compiled.match("slurm_node_rhel_10_0_x86_64")
