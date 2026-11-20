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

"""TC_FVT_routing_011: Catalog flexible group classification, routing, and bolt-on isolation.

Test plan reference:
  ER-ORCH-009-flexible-functional-groups-part2 / test-plan.md
  Priority: P0
  Requirement mapping: FR-1.1, FR-4.1, FR-4.4, FR-6.1, FR-6.2, AC-001, AC-008, AC-011, AC-012
  Environment: ENV-FVT
  Story: ER-ORCH-009-catalog-authoring-fixtures

Objective:
  Verify that catalog-defined flexible groups with the mandatory fg_ prefix classify
  as category 'flexible', precede the 'custom' catch-all, default to compute layer,
  have empty bolt-ons, and do not consume omnia_config.yml or storage_config.yml,
  while standard groups in the same catalog retain standard behavior and bolt-ons.
"""

# pylint: disable=redefined-outer-name,protected-access,wrong-import-position

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[5]
ORCHESTRATOR_ROOT = REPO_ROOT / "src" / "orchestrator"
FIXTURES_DIR = REPO_ROOT / "test" / "fixtures" / "catalogs" / "flexible_groups"
CLASSIFICATION_PATH = (
    ORCHESTRATOR_ROOT / "vars" / "functional_group_classification.yml"
)
GENERATE_FG_MODULE_PATH = (
    ORCHESTRATOR_ROOT / "plugins" / "modules" / "generate_functional_groups.py"
)
SOURCE_PLUGIN_ROOT = ORCHESTRATOR_ROOT / "plugins"

if str(SOURCE_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_PLUGIN_ROOT))

# Load generate_functional_groups module dynamically
spec = importlib.util.spec_from_file_location("generate_functional_groups", GENERATE_FG_MODULE_PATH)
fg_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fg_module)

from module_utils.orchestrator_validation.validators import pxe_mapping_validator  # noqa: E402


@pytest.fixture(scope="module")
def classification_data():
    """Load the functional group classification YAML file."""
    assert CLASSIFICATION_PATH.is_file(), f"Missing classification file: {CLASSIFICATION_PATH}"
    with open(CLASSIFICATION_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def categories(classification_data):
    """Return functional_group_categories dict."""
    return classification_data.get("functional_group_categories", {})


@pytest.fixture(scope="module")
def default_bolt_ons(classification_data):
    """Return default_bolt_ons dict."""
    return classification_data.get("default_bolt_ons", {})


@pytest.fixture(scope="module")
def valid_catalog():
    """Load the manual valid flexible groups catalog fixture."""
    fixture_path = FIXTURES_DIR / "manual_valid_fg_catalog.json"
    with open(fixture_path, encoding="utf-8") as fh:
        return json.load(fh)["catalog"]


@pytest.mark.fvt
@pytest.mark.order(40011)
class TestFlexibleGroupRoutingClassification:
    """TC_FVT_routing_011: Verify classification rules and routing for flexible groups."""

    def test_flexible_category_exists_and_precedes_custom(self, classification_data):
        """AC-012, FR-1.1: Category 'flexible' is defined and evaluated before 'custom'."""
        categories = classification_data.get("functional_group_categories", {})
        assert "flexible" in categories, "Category 'flexible' must exist"
        assert "custom" in categories, "Category 'custom' must exist"

        keys = list(categories.keys())
        assert keys.index("flexible") < keys.index("custom"), (
            "Category 'flexible' must precede 'custom'"
        )

    def test_flexible_category_properties(self, categories, default_bolt_ons):
        """AC-011, AC-012: Flexible category uses fg_ pattern, compute layer, and empty bolt-ons."""
        flex_cfg = categories["flexible"]
        assert flex_cfg.get("patterns") == ["^fg_"]
        assert flex_cfg.get("default_layer") == "compute"

        # AC-011: Flexible groups have NO bolt-ons
        assert default_bolt_ons.get("flexible") == []

    def test_catalog_fixture_flexible_groups_classify_as_flexible(self, valid_catalog, categories):
        """AC-012: Every fg_ group in the catalog fixture classifies as category 'flexible'."""
        fg_layers = [
            layer["name"] for layer in valid_catalog["functionallayer"]
            if layer["name"].startswith("fg_")
        ]
        assert len(fg_layers) == 10

        for fg_name in fg_layers:
            cat_name, layer, _ = fg_module.classify_functional_group(fg_name, categories)
            assert cat_name == "flexible", f"Group '{fg_name}' expected 'flexible'"
            assert layer == "compute", f"Group '{fg_name}' expected 'compute'"

    def test_standard_groups_in_catalog_preserve_classification_and_bolt_ons(
        self, valid_catalog, categories, default_bolt_ons
    ):
        """AC-008, AC-011: Standard groups in the same catalog retain category and bolt-ons."""
        std_layers = [
            layer["name"] for layer in valid_catalog["functionallayer"]
            if not layer["name"].startswith("fg_")
        ]
        assert len(std_layers) > 0, "Expected standard groups in catalog fixture"

        expected_classifications = {
            "os_rhel_10_2_x86_64": ("os_only", "compute"),
            "slurm_control_node_rhel_10_2_x86_64": ("slurm", "management"),
            "slurm_node_rhel_10_0_aarch64": ("slurm", "compute"),
        }

        for std_name in std_layers:
            if std_name in expected_classifications:
                expected_cat, expected_layer = expected_classifications[std_name]
                cat_name, layer, _ = fg_module.classify_functional_group(std_name, categories)
                assert cat_name == expected_cat
                assert layer == expected_layer

        # Standard categories retain their defined bolt-ons
        assert "slurm_config" in default_bolt_ons.get("slurm", [])
        assert "mount_config" in default_bolt_ons.get("slurm", [])

    def test_non_fg_custom_groups_fall_through_to_custom(self, categories):
        """FR-1.1: Groups without fg_ or standard prefixes fall through to 'custom'."""
        custom_names = [
            "custom_worker_x86_64",
            "batch_job_runner_x86_64",
            "unregistered_node_group",
        ]
        for name in custom_names:
            cat_name, layer, _ = fg_module.classify_functional_group(name, categories)
            assert cat_name == "custom", f"Group '{name}' classified as '{cat_name}'"
            assert layer == "compute", f"Group '{name}' layer is '{layer}'"

    def test_pxe_mapping_routing_matches_catalog_flexible_groups(self, tmp_path, valid_catalog):
        """AC-001, AC-009: PXE mapping rows for catalog flexible groups correlate successfully."""
        catalog_path = tmp_path / "catalog_rhel.json"
        catalog_path.write_text(json.dumps({"catalog": valid_catalog}), encoding="utf-8")

        fg_groups = [
            l["name"] for l in valid_catalog["functionallayer"]
            if l["name"].startswith("fg_")
        ]

        rows = []
        for i, group in enumerate(fg_groups, start=1):
            row_dict = {
                "FUNCTIONAL_GROUP_NAME": group,
                "GROUP_NAME": f"grp{i}",
                "HOSTNAME": f"node{i}",
                "ADMIN_MAC": f"00:11:22:33:44:{i:02x}",
                "ADMIN_IP": f"10.0.0.{i}",
                "SERVICE_TAG": f"TAG{i:04d}",
                "PARENT_SERVICE_TAG": "",
                "BMC_MAC": f"ff:ee:dd:cc:bb:{i:02x}",
                "BMC_IP": f"10.1.0.{i}",
                "IB_NIC_NAME": "",
                "IB_IPV4": "",
                "IB_IPV6": "",
            }
            rows.append((i, row_dict))

        errors = []
        config_data = {"catalog_file_path": str(catalog_path)}
        pxe_mapping_validator._validate_catalog_functional_groups(
            rows, config_data, str(tmp_path), errors, logger=None
        )
        assert not errors, f"Unexpected mapping-to-catalog correlation errors: {errors}"

    def test_pxe_mapping_rejects_uncataloged_flexible_group(
        self, tmp_path, valid_catalog
    ):
        """AC-001, FR-1.1: A flexible group not in catalog is rejected in PXE mapping."""
        catalog_path = tmp_path / "catalog_rhel.json"
        catalog_path.write_text(json.dumps({"catalog": valid_catalog}), encoding="utf-8")

        rows = [(
            1,
            {
                "FUNCTIONAL_GROUP_NAME": "fg_nonexistent_group_rhel_10_2_x86_64",
                "GROUP_NAME": "grp1",
                "HOSTNAME": "node1",
                "ADMIN_MAC": "00:11:22:33:44:01",
                "ADMIN_IP": "10.0.0.1",
            }
        )]
        errors = []
        config_data = {"catalog_file_path": str(catalog_path)}
        pxe_mapping_validator._validate_catalog_functional_groups(
            rows, config_data, str(tmp_path), errors, logger=None
        )
        assert errors, "Expected error for uncataloged flexible group"
        assert any("fg_nonexistent_group_rhel_10_2_x86_64" in e for e in errors)
