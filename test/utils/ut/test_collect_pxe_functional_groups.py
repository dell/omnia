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
Regression tests for OMN-DEF #866.

collect_pxe.yml's input/schema/validation stack was missing the
``login_compiler_node_x86_64`` functional group — only the aarch64 variant
was recognized, even though every other functional group in the file
distinguishes x86_64 from aarch64. These tests pin the fix in place across
the validator, the JSON schema, the Ansible validation role, and the
collect_pxe.yml input file/example.
"""

# pylint: disable=missing-function-docstring,redefined-outer-name

import importlib.util
import json
import re
import sys
import types

import pytest
import yaml

NEW_GROUP = "login_compiler_node_x86_64"


def _load_validator_module(validators_dir):
    """Import collect_pxe_config_validator.py without the real ansible package."""
    module_path = validators_dir / "collect_pxe_config_validator.py"
    assert module_path.exists(), f"validator module not found: {module_path}"

    # Stub out ansible.module_utils.input_validation.messages so the module
    # can be imported standalone, the same way other domain UT suites do.
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


class TestValidFunctionalGroupsSet:
    """VALID_FUNCTIONAL_GROUPS must include both compiler-node architectures."""

    def test_x86_64_compiler_group_is_valid(self, validator_module):
        assert NEW_GROUP in validator_module.VALID_FUNCTIONAL_GROUPS

    def test_aarch64_compiler_group_still_valid(self, validator_module):
        assert "login_compiler_node_aarch64" in validator_module.VALID_FUNCTIONAL_GROUPS

    def test_validate_accepts_x86_64_compiler_group(self, validator_module):
        errors = validator_module.validate({NEW_GROUP: ["192.168.1.55"]})
        assert errors == []

    def test_validate_rejects_unknown_group(self, validator_module):
        errors = validator_module.validate({"not_a_real_group": ["192.168.1.55"]})
        assert len(errors) == 1
        assert "not_a_real_group" in errors[0]


class TestCollectPxeSchema:
    """collect_pxe_config.json must accept the x86_64 compiler-node key."""

    def test_schema_accepts_x86_64_compiler_group(self, schema_dir):
        schema = json.loads(
            (schema_dir / "collect_pxe_config.json").read_text(encoding="utf-8")
        )
        patterns = list(schema["patternProperties"].keys())
        assert any(re.match(pattern, NEW_GROUP) for pattern in patterns)

    def test_schema_still_accepts_aarch64_compiler_group(self, schema_dir):
        schema = json.loads(
            (schema_dir / "collect_pxe_config.json").read_text(encoding="utf-8")
        )
        patterns = list(schema["patternProperties"].keys())
        assert any(
            re.match(pattern, "login_compiler_node_aarch64") for pattern in patterns
        )


class TestValidateCollectConfigRole:
    """The Ansible validation role's group-name pattern must cover it too."""

    def _functional_group_pattern(self, src_dir):
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

    def test_pattern_matches_x86_64_compiler_group(self, src_dir):
        pattern = self._functional_group_pattern(src_dir)
        assert pattern.match(NEW_GROUP)

    def test_error_message_documents_login_compiler_node_role(self, src_dir):
        vars_path = src_dir / "roles" / "validate_collect_config" / "vars" / "main.yml"
        with open(vars_path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        assert "login_compiler_node" in data["invalid_group_name_msg"]


class TestCollectPxeInputFile:
    """The shipped example input file documents the new group."""

    def test_input_file_has_x86_64_compiler_group_key(self, input_dir):
        collect_pxe_path = input_dir / "collect_pxe.yml"
        with open(collect_pxe_path, encoding="utf-8") as handle:
            content = handle.read()
        assert f"{NEW_GROUP}:" in content

    def test_input_file_parses_with_new_group_populated(self, input_dir):
        collect_pxe_path = input_dir / "collect_pxe.yml"
        text = collect_pxe_path.read_text(encoding="utf-8")
        # Simulate a user populating the new group and confirm it round-trips
        # through YAML parsing like every other functional group.
        text += f"\n{NEW_GROUP}:\n  - 10.0.0.55\n"
        parsed = yaml.safe_load(text)
        assert parsed[NEW_GROUP] == ["10.0.0.55"]


class TestPrepareTaskCombinesBothArchitectures:
    """prepare.yml must merge x86_64 + aarch64 compiler nodes like slurm_nodes."""

    def test_prepare_yml_has_x86_64_compiler_pattern_bucket(self, src_dir):
        prepare_path = src_dir / "roles" / "log_collector" / "tasks" / "prepare.yml"
        with open(prepare_path, encoding="utf-8") as handle:
            tasks = yaml.safe_load(handle)

        set_fact_task = next(
            task
            for task in tasks
            if task.get("name")
            == "Set node lists from YAML (functional groups with architecture, "
            "OS/version-agnostic)"
        )
        facts = set_fact_task["ansible.builtin.set_fact"]
        assert "login_compiler_nodes_x86_pattern" in facts["login_compiler_nodes_x86"]

    def test_prepare_yml_combines_compiler_architectures(self, src_dir):
        prepare_path = src_dir / "roles" / "log_collector" / "tasks" / "prepare.yml"
        with open(prepare_path, encoding="utf-8") as handle:
            tasks = yaml.safe_load(handle)

        combine_task = next(
            task
            for task in tasks
            if task.get("name") == "Combine login compiler nodes from both architectures"
        )
        expr = combine_task["ansible.builtin.set_fact"]["login_compiler_nodes"]
        assert "login_compiler_nodes_x86" in expr
        assert "login_compiler_nodes_arm" in expr
