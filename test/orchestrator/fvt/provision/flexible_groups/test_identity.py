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

"""TC_FVT_identity_001: Validate flexible-group identity and platform boundary.

Test plan reference:
  ER-ORCH-009-flexible-functional-groups-part2 / test-plan.md § 4
  Priority: P0
  Requirement mapping: FR-1.1, AC-001, AC-003, AC-012
  Environment: ENV-FVT
  Story: ER-ORCH-009-role-topology-routing

Objective:
  Accept valid fg_ groups and reject invalid prefix, suffix, count, or
  architecture before mutation.

Scenarios:
  1. Accept valid flexible-group identities
     GIVEN a catalog contains no more than ten fg_-prefixed groups with valid
     platform suffixes
     WHEN flexible-group validation runs
     THEN the groups pass and predefined groups are excluded from the count

  2. Reject an invalid identity boundary
     GIVEN a flexible group lacks fg_, exceeds the count, lacks the suffix,
     or uses an unsupported architecture
     WHEN validation runs
     THEN validation fails before OpenCHAMI, BSS, metadata, image, or node
     mutation

Evidence required:
  Validation result with sanitized group and violated rule.
Not testing:
  Workload scheduler behavior.
"""

# pylint: disable=wrong-import-position

import json
import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[5]
ORCHESTRATOR_ROOT = REPO_ROOT / "src" / "orchestrator"
REPO_MANAGER_ROOT = REPO_ROOT / "src" / "repo_manager"
FIXTURES_DIR = REPO_ROOT / "test" / "fixtures" / "catalogs" / "flexible_groups"
SOURCE_PLUGIN_ROOT = ORCHESTRATOR_ROOT / "plugins"
REPO_MANAGER_PLUGIN_ROOT = REPO_MANAGER_ROOT / "plugins" / "module_utils"

if str(SOURCE_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_PLUGIN_ROOT))
if str(REPO_MANAGER_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_MANAGER_PLUGIN_ROOT))

from module_utils.orchestrator_validation.validators import (  # noqa: E402
    functional_group_config_validator as functional_validator,
)
from catalog.validator import validate_catalog  # noqa: E402
SOURCE_PLUGIN_ROOT = ORCHESTRATOR_ROOT / "plugins"
if str(SOURCE_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_PLUGIN_ROOT))


from module_utils.orchestrator_validation.validators import (
    functional_group_config_validator as functional_validator,
)


# ── Helpers ─────────────────────────────────────────────────────────────


def _write_mapping(path, groups):
    """Write a PXE mapping CSV with one node per group."""
    lines = [
        "FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,PARENT_SERVICE_TAG,"
        "HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP,IB_NIC_NAME,IB_IP"
    ]
    for i, group in enumerate(groups):
        mac = f"00:11:22:33:44:{i:02x}"
        lines.append(
            f"{group},group-{i},tag-{i},,node-{i},{mac},"
            f"192.0.2.{10 + i},{mac},192.0.2.{110 + i},,"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _validate(tmp_path, config, groups, **orchestrator):
    """Run the functional_group_config_validator for the given groups."""
    mapping = tmp_path / "pxe_mapping_file.csv"
    _write_mapping(mapping, groups)
    return functional_validator.validate(
        config, {"pxe_mapping_file_path": str(mapping), **orchestrator}, str(tmp_path)
    )


# ── Scenario 1: Accept valid flexible-group identities ─────────────────


@pytest.mark.fvt
@pytest.mark.order(40001)
class TestValidIdentities:
    """Valid fg_ groups with proper platform suffixes pass validation."""

    def test_single_valid_fg_group(self, tmp_path):
        """ORCH_FVT_FG_V001: A single valid fg_ group passes validation."""
        group = "fg_research_rhel_10_0_x86_64"
        errors = _validate(
            tmp_path,
            {"groups": {group: {"boot_kernel_params": "audit=1"}}},
            [group],
        )
        assert not errors, f"Unexpected errors: {errors}"

    def test_multiple_valid_fg_groups(self, tmp_path):
        """ORCH_FVT_FG_V002: Multiple valid fg_ groups (up to 10) pass validation."""
        groups = [
            "fg_web_rhel_10_0_x86_64",
            "fg_db_rhel_10_2_x86_64",
            "fg_compute_rhel_10_0_aarch64",
        ]
        config = {"groups": {g: {} for g in groups}}
        errors = _validate(tmp_path, config, groups)
        assert not errors, f"Unexpected errors: {errors}"

    def test_ten_fg_groups_accepted(self, tmp_path):
        """ORCH_FVT_FG_V003: Exactly ten fg_ groups are accepted."""
        groups = [f"fg_group{i}_rhel_10_0_x86_64" for i in range(10)]
        config = {"groups": {g: {} for g in groups}}
        errors = _validate(tmp_path, config, groups)
        assert not errors, f"Unexpected errors: {errors}"

    def test_predefined_groups_excluded_from_fg_count(self, tmp_path):
        """ORCH_FVT_FG_V004: Predefined groups are not counted toward the fg_ limit."""
        fg_groups = [f"fg_group{i}_rhel_10_0_x86_64" for i in range(10)]
        all_groups = fg_groups + ["slurm_node_rhel_10_0_x86_64"]
        config = {"groups": {g: {} for g in fg_groups}}
        errors = _validate(tmp_path, config, all_groups)
        assert not errors, f"Unexpected errors: {errors}"

    def test_aarch64_architecture_accepted(self, tmp_path):
        """ORCH_FVT_FG_V005: aarch64 architecture is a valid platform suffix."""
        group = "fg_hpc_rhel_10_0_aarch64"
        errors = _validate(
            tmp_path,
            {"groups": {group: {}}},
            [group],
        )
        assert not errors, f"Unexpected errors: {errors}"

    def test_manual_valid_catalog_fixture(self, tmp_path):
        """FR-1.1, AC-001, AC-008: Valid catalog fixture passes identity and count checks."""
        fixture_path = FIXTURES_DIR / "manual_valid_fg_catalog.json"
        assert fixture_path.is_file(), f"Fixture missing: {fixture_path}"
        with open(fixture_path, encoding="utf-8") as fh:
            cat_data = json.load(fh)

        # Catalog validator passes with 0 errors
        schema_path = str(REPO_MANAGER_ROOT / "schemas" / "catalog_schema.json")
        issues = validate_catalog(cat_data, schema_path)
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        assert not errors, f"Unexpected catalog validation errors: {errors}"

        # Downstream orchestrator validation accepts all fg_ groups
        fg_groups = [
            l["name"] for l in cat_data["catalog"]["functionallayer"]
            if l["name"].startswith("fg_")
        ]
        assert len(fg_groups) == 10
        all_groups = [l["name"] for l in cat_data["catalog"]["functionallayer"]]
        config = {"groups": {g: {} for g in fg_groups}}
        orch_errors = _validate(tmp_path, config, all_groups)
        assert not orch_errors, f"Unexpected orchestrator errors: {orch_errors}"

    def test_reviewed_generated_catalog_fixture(self, tmp_path):
        """FR-1.1, ER-BSM-001: Operator-reviewed generated catalog passes downstream validation."""
        fixture_path = FIXTURES_DIR / "reviewed_generated_fg_catalog.json"
        assert fixture_path.is_file(), f"Fixture missing: {fixture_path}"
        with open(fixture_path, encoding="utf-8") as fh:
            cat_data = json.load(fh)

        schema_path = str(REPO_MANAGER_ROOT / "schemas" / "catalog_schema.json")
        issues = validate_catalog(cat_data, schema_path)
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        assert not errors, f"Reviewed generated catalog should pass: {errors}"

        fg_groups = [
            l["name"] for l in cat_data["catalog"]["functionallayer"]
            if l["name"].startswith("fg_")
        ]
        config = {"groups": {g: {} for g in fg_groups}}
        orch_errors = _validate(tmp_path, config, fg_groups)
        assert not orch_errors, f"Unexpected orchestrator errors: {orch_errors}"


# ── Scenario 2: Reject an invalid identity boundary ────────────────────


@pytest.mark.fvt
@pytest.mark.order(40002)
class TestInvalidIdentities:
    """Invalid prefix, suffix, count, or architecture fail before mutation."""

    @pytest.mark.parametrize(
        "group",
        [
            "slurm_node_rhel_10_0_x86_64",
            "service_kube_control_plane_rhel_10_0_x86_64",
            "service_kube_node_rhel_10_0_x86_64",
            "login_node_rhel_10_0_x86_64",
            "os_rhel_10_0_x86_64",
        ],
    )
    def test_predefined_groups_rejected_in_fg_config(self, tmp_path, group):
        """ORCH_FVT_FG_V006: Predefined group names cannot appear in
        functional_group_config.yml group keys."""
        errors = _validate(
            tmp_path,
            {"groups": {group: {"boot_kernel_params": "audit=1"}}},
            [group],
        )
        assert errors, f"Expected errors for predefined group '{group}'"
        assert any("flexible functional group" in e for e in errors)

    def test_non_fg_prefix_rejected(self, tmp_path):
        """ORCH_FVT_FG_V007: Groups without fg_ prefix are rejected."""
        group = "custom_research_rhel_10_0_x86_64"
        errors = _validate(
            tmp_path,
            {"groups": {group: {"boot_kernel_params": "audit=1"}}},
            [group],
        )
        assert errors, "Expected errors for non-fg_ prefix"

    def test_empty_config_is_inactive(self, tmp_path):
        """An empty configuration template changes nothing."""
        group = "fg_research_rhel_10_0_x86_64"
        errors = _validate(tmp_path, {"common": {}, "groups": {}}, [group])
        assert not errors, f"Unexpected errors: {errors}"

    def test_invalid_missing_prefix_fixture_rejected(self):
        """FR-1.1: Catalog fixture with missing fg_ prefix is rejected."""
        fixture_path = FIXTURES_DIR / "invalid_missing_prefix_catalog.json"
        with open(fixture_path, encoding="utf-8") as fh:
            cat_data = json.load(fh)
        issues = validate_catalog(cat_data)
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        assert errors, "Expected missing fg_ prefix error"
        assert any("mandatory 'fg_' prefix" in e for e in errors)

    def test_invalid_count_exceeded_fixture_rejected(self):
        """AC-001: Catalog fixture with > 10 flexible groups is rejected."""
        fixture_path = FIXTURES_DIR / "invalid_count_exceeded_catalog.json"
        with open(fixture_path, encoding="utf-8") as fh:
            cat_data = json.load(fh)
        issues = validate_catalog(cat_data)
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        assert errors, "Expected count boundary error"
        assert any("maximum allowed is 10" in e for e in errors)

    def test_invalid_suffix_missing_fixture_rejected(self):
        """FR-1.1: Catalog fixture with missing platform suffix is rejected."""
        fixture_path = FIXTURES_DIR / "invalid_suffix_missing_catalog.json"
        with open(fixture_path, encoding="utf-8") as fh:
            cat_data = json.load(fh)
        issues = validate_catalog(cat_data)
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        assert errors, "Expected missing platform suffix error"
        assert any("platform suffix" in e for e in errors)

    def test_invalid_architecture_fixture_rejected(self):
        """AC-001, AC-003: Catalog fixture with unsupported architecture is rejected (blocking)."""
        fixture_path = FIXTURES_DIR / "invalid_architecture_catalog.json"
        with open(fixture_path, encoding="utf-8") as fh:
            cat_data = json.load(fh)
        issues = validate_catalog(cat_data)
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        assert errors, "Expected unsupported architecture error"
        assert any("unsupported architecture 'ppc64le'" in e for e in errors)

    def test_unreviewed_generated_fixture_rejected(self):
        """FR-1.1, ER-BSM-001: Unreviewed generated catalog fixture is rejected before mutation."""
        fixture_path = FIXTURES_DIR / "unreviewed_generated_catalog.json"
        with open(fixture_path, encoding="utf-8") as fh:
            cat_data = json.load(fh)
        issues = validate_catalog(cat_data)
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        assert errors, "Expected operator review gate error"
        assert any("operator review approval" in e for e in errors)

    def test_warning_os_version_fixture_warns_without_blocking(self):
        """AC-003: Non-RHEL 10.0/10.2 syntactically valid OS version warns without blocking."""
        fixture_path = FIXTURES_DIR / "warning_os_version_catalog.json"
        with open(fixture_path, encoding="utf-8") as fh:
            cat_data = json.load(fh)
        issues = validate_catalog(cat_data)
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        warnings = [i["message"] for i in issues if i["severity"] == "warning"]
        assert not errors, f"Unqualified OS should not produce blocking errors: {errors}"
        assert warnings, "Expected non-blocking advisory warning"
        assert any("only RHEL 10.0 and 10.2 are qualified" in w for w in warnings)
