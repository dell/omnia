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

"""TC_UT_classification_001: Flexible-group classifier.

Test plan reference:
  ER-ORCH-009-flexible-functional-groups-part2 / test-plan.md § 6
  Priority: P0
  HLD mapping: Section 3.0 functional-group classification
  ER mapping: FR-1.1, AC-001, AC-012
  Story: ER-ORCH-009-role-topology-routing

Scenarios:
  1. Classify an fg_ group as flexible
     GIVEN isolated classification rules place ^fg_ before the catch-all
     WHEN a valid name is classified
     THEN category flexible and empty default bolt-ons are returned

  2. Preserve predefined and reject malformed identities
     GIVEN predefined or malformed names
     WHEN classification validation runs
     THEN predefined categories remain unchanged and malformed flexible input
     is rejected
"""

import re
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR_ROOT = REPO_ROOT / "src" / "orchestrator"
CLASSIFICATION_PATH = ORCHESTRATOR_ROOT / "vars" / "functional_group_classification.yml"


@pytest.fixture(scope="module")
def classification() -> dict:
    """Load the canonical classification rules."""
    return yaml.safe_load(CLASSIFICATION_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def categories(classification: dict) -> dict:
    return classification["functional_group_categories"]


@pytest.fixture(scope="module")
def provisioning_map(classification: dict) -> dict:
    return classification["category_provisioning_map"]


@pytest.fixture(scope="module")
def bolt_ons(classification: dict) -> dict:
    return classification["default_bolt_ons"]


# ── Scenario 1: Classify an fg_ group as flexible ──────────────────────


def _classify(categories: dict, name: str) -> str | None:
    """Return the first matching category for *name*, or None."""
    for category, meta in categories.items():
        for pattern in meta["patterns"]:
            if re.match(pattern, name):
                return category
    return None


class TestFlexibleClassification:
    """fg_ groups classify as 'flexible' before the custom catch-all."""

    def test_flexible_precedes_custom_in_category_order(self, categories):
        """AC-001: ^fg_ pattern is evaluated before the .* catch-all."""
        names = list(categories)
        assert "flexible" in names
        assert "custom" in names
        assert names.index("flexible") < names.index("custom")

    def test_flexible_pattern_is_fg_prefix(self, categories):
        """FR-1.1: The flexible category uses exactly ^fg_ as its pattern."""
        assert categories["flexible"]["patterns"] == ["^fg_"]

    def test_flexible_maps_to_manage_functional_group(self, provisioning_map):
        """FR-4.1: Flexible groups route to manage_functional_group playbook."""
        assert provisioning_map["flexible"] == "manage_functional_group"

    def test_flexible_has_empty_bolt_ons(self, bolt_ons):
        """AC-012: Flexible groups carry no default bolt-on services."""
        assert bolt_ons["flexible"] == []

    @pytest.mark.parametrize(
        "name",
        [
            "fg_webserver_rhel_10_0_x86_64",
            "fg_research_rhel_10_2_x86_64",
            "fg_hpc_worker_rhel_10_0_aarch64",
            "fg_minimal_rhel_10_2_aarch64",
        ],
    )
    def test_valid_fg_names_classify_as_flexible(self, categories, name):
        """FR-1.1: Valid fg_ names match 'flexible', not 'custom'."""
        assert _classify(categories, name) == "flexible"

    def test_flexible_default_layer_is_compute(self, categories):
        """Flexible groups default to the compute layer."""
        assert categories["flexible"]["default_layer"] == "compute"

    def test_up_to_ten_flexible_groups_are_supported(self, categories):
        """AC-001: The classifier does not impose count limits itself; ten
        groups are supported by the validator. The classification rules
        must match any number of fg_ names without inherent restriction."""
        names = [f"fg_group{i}_rhel_10_0_x86_64" for i in range(10)]
        for name in names:
            assert _classify(categories, name) == "flexible"


# ── Scenario 2: Preserve predefined and reject malformed identities ────


class TestPredefinedPreservation:
    """Predefined categories remain unchanged; only fg_ matches flexible."""

    @pytest.mark.parametrize(
        "name, expected_category",
        [
            ("service_kube_control_plane_rhel_10_0_x86_64", "kubernetes"),
            ("service_kube_node_rhel_10_0_x86_64", "kubernetes"),
            ("slurm_node_rhel_10_0_x86_64", "slurm"),
            ("slurm_control_node_rhel_10_0_x86_64", "slurm"),
            ("login_node_rhel_10_0_x86_64", "login"),
            ("login_compiler_node_rhel_10_0_x86_64", "login"),
            ("os_rhel_10_0_x86_64", "os_only"),
        ],
    )
    def test_predefined_groups_keep_their_category(
        self, categories, name, expected_category
    ):
        """AC-012: Predefined group categories are never overridden by fg_."""
        assert _classify(categories, name) == expected_category

    @pytest.mark.parametrize(
        "name",
        [
            "custom_research_rhel_10_0_x86_64",
            "mygroup_rhel_10_0_x86_64",
            "research_rhel_10_0_x86_64",
        ],
    )
    def test_non_fg_non_predefined_groups_are_custom(self, categories, name):
        """Groups without fg_ prefix that don't match predefined patterns
        fall through to the custom catch-all."""
        assert _classify(categories, name) == "custom"

    @pytest.mark.parametrize(
        "name",
        [
            "FG_invalid_upper_case",
            "fG_mixed_case",
            "f_g_separated",
        ],
    )
    def test_case_sensitive_fg_prefix(self, categories, name):
        """FR-1.1: Only lowercase ^fg_ matches flexible; variants fall
        through to custom."""
        assert _classify(categories, name) != "flexible"

    def test_each_predefined_category_has_provisioning_mapping(
        self, categories, provisioning_map
    ):
        """Every predefined category must have a provisioning map entry."""
        for category in categories:
            assert category in provisioning_map, (
                f"Category '{category}' missing from category_provisioning_map"
            )

    def test_each_predefined_category_has_bolt_on_entry(
        self, categories, bolt_ons
    ):
        """Every predefined category must have a default_bolt_ons entry."""
        for category in categories:
            assert category in bolt_ons, (
                f"Category '{category}' missing from default_bolt_ons"
            )
