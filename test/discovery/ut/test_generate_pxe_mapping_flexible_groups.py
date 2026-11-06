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
ER-ORCH-009 (AC-009): Discovery's generate_pxe_mapping must accept and preserve
flexible functional-group names carrying the mandatory ``fg_`` prefix with the
OS/version/architecture suffix convention, so they survive the operator-reviewed
mapping handoff to Orchestrator.
"""

# pylint: disable=missing-function-docstring,redefined-outer-name

import importlib.util
import sys
import types

import pytest


def _load_generate_pxe_mapping(src_dir):
    module_path = src_dir / "plugins" / "modules" / "generate_pxe_mapping.py"
    assert module_path.exists(), f"module not found: {module_path}"

    # Stub ansible.module_utils.basic so the module imports standalone.
    basic_mod = types.ModuleType("ansible.module_utils.basic")
    basic_mod.AnsibleModule = object
    for name, mod in [
        ("ansible", types.ModuleType("ansible")),
        ("ansible.module_utils", types.ModuleType("ansible.module_utils")),
        ("ansible.module_utils.basic", basic_mod),
    ]:
        sys.modules.setdefault(name, mod)

    spec = importlib.util.spec_from_file_location("generate_pxe_mapping", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def pxe_module(src_dir):
    return _load_generate_pxe_mapping(src_dir)


def test_fg_prefix_is_supported(pxe_module):
    assert "fg_" in pxe_module.SUPPORTED_ROLE_PREFIXES


@pytest.mark.parametrize(
    "group",
    [
        "fg_webserver_rhel_10_2_x86_64",
        "fg_mpi_worker_rhel_10_0_aarch64",
        "fg_webserver_x86_64",
    ],
)
def test_flexible_groups_are_supported(pxe_module, group):
    assert pxe_module._is_supported_functional_group(group)


def test_flexible_group_without_architecture_is_rejected(pxe_module):
    assert not pxe_module._is_supported_functional_group("fg_webserver")


def test_flexible_group_os_version_injection_preserves_prefix(pxe_module):
    injected = pxe_module._inject_os_version("fg_webserver_x86_64", "rhel", "10.2")
    assert injected == "fg_webserver_rhel_10_2_x86_64"


def test_existing_flexible_os_version_segment_is_preserved(pxe_module):
    name = "fg_webserver_rhel_10_2_x86_64"
    assert pxe_module._inject_os_version(name, "rhel", "10.0") == name
