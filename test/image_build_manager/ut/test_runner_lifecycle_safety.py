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
"""Regression tests for non-destructive default runner lifecycles."""

# Small protocol fakes keep collection-hook tests independent of pytest internals.
# pylint: disable=missing-function-docstring,too-few-public-methods

import importlib.util
from pathlib import Path
from types import SimpleNamespace

from library.vars.domain_vars import EXCLUDE_TAGS, SUITE_EXEC_OWNERS
from library.vars.test_case_vars import TEST_CASES


MODULE_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "image_build_manager_root_conftest",
    MODULE_ROOT / "conftest.py",
)
RUNNER_HOOKS = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(RUNNER_HOOKS)


class _Config:
    def __init__(self, marker_expression=""):
        self.marker_expression = marker_expression

    def getoption(self, name, default=""):
        return self.marker_expression if name == "--marker" else default


class _Item:
    def __init__(self):
        self.nodeid = "nft/test_performance.py::test_cleanup_performance"
        self._markers = {
            "nft": SimpleNamespace(args=()),
            "destructive": SimpleNamespace(args=()),
            "order": SimpleNamespace(args=(3,)),
        }
        self.added_markers = []

    def get_closest_marker(self, name):
        return self._markers.get(name)

    def add_marker(self, marker):
        self.added_markers.append(marker)


def test_default_nft_skips_destructive_cleanup():
    item = _Item()

    RUNNER_HOOKS.pytest_collection_modifyitems(None, _Config(), [item])

    assert any(marker.mark.name == "skip" for marker in item.added_markers)


def test_destructive_nft_marker_explicitly_enables_cleanup():
    item = _Item()

    RUNNER_HOOKS.pytest_collection_modifyitems(
        None,
        _Config("destructive"),
        [item],
    )

    assert not any(marker.mark.name == "skip" for marker in item.added_markers)


def test_default_fvt_verification_excludes_cleanup_flows():
    assert EXCLUDE_TAGS == ["cleanup", "cleanup_images"]


def test_catalog_reuse_e2e_owns_execution_and_restores_state():
    assert "catalog_reuse" in SUITE_EXEC_OWNERS["build"]
    assert (
        TEST_CASES["catalog_suite_restores_target_state"]["id"]
        == "IMGBM_FVT_CATALOG_REUSE_V011"
    )
