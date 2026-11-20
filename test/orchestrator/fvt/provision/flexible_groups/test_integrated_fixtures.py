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

"""TC_FVT_integrated_016: Integrated flexible group catalog contract verification.

Test plan reference:
  ER-ORCH-009-flexible-functional-groups-part2 / test-plan.md
  Priority: P0
  Requirement mapping: FR-1.1, FR-3.1, FR-6.1, FR-6.2, AC-001, AC-003, AC-004, AC-008, AC-012
  Environment: ENV-FVT
  Story: ER-ORCH-009-catalog-authoring-fixtures

Objective:
  Perform integrated end-to-end verification of all flexible group catalog fixtures:
  - Both positive fixtures (manual and operator-reviewed generated) satisfy repo_manager,
    image_build_manager, and orchestrator contracts.
  - Every negative fixture is rejected with the exact boundary violation before mutation.
  - Advisory warnings (non-RHEL 10.0/10.2) warn without blocking execution.
  - Standard bundled catalogs remain 100% backward compatible with 0 regressions.
  - Image Build Manager parse_catalog correctly processes flexible group layers.
"""

# pylint: disable=redefined-outer-name,protected-access,wrong-import-position

import importlib.util
import json
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[5]
FIXTURES_DIR = REPO_ROOT / "test" / "fixtures" / "catalogs" / "flexible_groups"
REPO_MANAGER_ROOT = REPO_ROOT / "src" / "repo_manager"
IBM_ROOT = REPO_ROOT / "src" / "image_build_manager"
SAMPLES_DIR = REPO_ROOT / "src" / "main" / "samples" / "catalogs"

RM_SCHEMA_PATH = REPO_MANAGER_ROOT / "schemas" / "catalog_schema.json"
IBM_SCHEMA_PATH = (
    IBM_ROOT / "plugins" / "module_utils" / "input_validation" / "schema" / "catalog.json"
)

REPO_MANAGER_PLUGIN_ROOT = REPO_MANAGER_ROOT / "plugins" / "module_utils"
if str(REPO_MANAGER_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_MANAGER_PLUGIN_ROOT))

IBM_PLUGINS_ROOT = IBM_ROOT / "plugins"
if str(IBM_PLUGINS_ROOT) not in sys.path:
    sys.path.insert(0, str(IBM_PLUGINS_ROOT))

ORCHESTRATOR_PLUGIN_ROOT = REPO_ROOT / "src" / "orchestrator" / "plugins"
if str(ORCHESTRATOR_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ORCHESTRATOR_PLUGIN_ROOT))

from catalog.validator import validate_catalog  # noqa: E402
from module_utils.image_fallback_resolver import (  # noqa: E402
    resolve_boot_image_fallback,
)


@pytest.fixture(scope="module")
def rm_schema():
    """Load repo_manager catalog JSON schema."""
    with open(RM_SCHEMA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def ibm_schema():
    """Load image_build_manager catalog JSON schema."""
    with open(IBM_SCHEMA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.mark.fvt
@pytest.mark.order(40016)
class TestIntegratedCatalogFixtures:
    """TC_FVT_integrated_016: Comprehensive validation of all catalog fixtures."""

    def test_positive_manual_catalog_satisfies_all_contracts(
        self, rm_schema, ibm_schema
    ):
        """AC-001, AC-008, AC-012: Manual valid catalog passes all schema/business validation."""
        path = FIXTURES_DIR / "manual_valid_fg_catalog.json"
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)

        # 1. Repo Manager JSON Schema
        jsonschema.validate(data, rm_schema)

        # 2. Image Build Manager JSON Schema
        jsonschema.validate(data, ibm_schema)

        # 3. Comprehensive catalog validator
        issues = validate_catalog(data, str(RM_SCHEMA_PATH))
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        assert not errors, f"Manual valid catalog produced errors: {errors}"

        # 4. Contains exactly 10 flexible groups and standard groups coexist
        fg_layers = [
            l["name"] for l in data["catalog"]["functionallayer"]
            if l["name"].startswith("fg_")
        ]
        std_layers = [
            l["name"] for l in data["catalog"]["functionallayer"]
            if not l["name"].startswith("fg_")
        ]
        assert len(fg_layers) == 10
        assert len(std_layers) >= 3

    def test_positive_reviewed_generated_catalog_satisfies_all_contracts(
        self, rm_schema, ibm_schema
    ):
        """FR-1.1, AC-001, ER-BSM-001: Reviewed generated catalog satisfies all contracts."""
        path = FIXTURES_DIR / "reviewed_generated_fg_catalog.json"
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)

        # 1. Schemas
        jsonschema.validate(data, rm_schema)
        jsonschema.validate(data, ibm_schema)

        # 2. Comprehensive validator
        issues = validate_catalog(data, str(RM_SCHEMA_PATH))
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        assert not errors, f"Reviewed generated catalog produced errors: {errors}"

        # 3. Retains operator review evidence
        cat = data["catalog"]
        assert cat.get("generated") is True
        assert cat.get("operator_review", {}).get("approved") is True
        assert (
            cat.get("operator_review", {}).get("authoring_contract")
            == "ER-BSM-001-nersc-ai-skills-catalog-authoring"
        )

    @pytest.mark.parametrize(
        ("fixture_name", "expected_snippet"),
        [
            ("invalid_missing_prefix_catalog.json", "missing the mandatory 'fg_' prefix"),
            ("invalid_count_exceeded_catalog.json", "maximum allowed is 10"),
            ("invalid_suffix_missing_catalog.json", "lacks required platform suffix"),
            ("invalid_architecture_catalog.json", "unsupported architecture 'ppc64le'"),
            ("broken_referential_group_catalog.json", "references missing group"),
            ("broken_referential_package_catalog.json", "references missing package"),
            ("broken_baseos_catalog.json", "must have exactly one baseos group"),
            ("unreviewed_generated_catalog.json", "lacks valid operator review approval"),
            ("invalid_package_image_catalog.json", "missing 'tag'"),
        ],
    )
    def test_negative_catalog_fixtures_rejected(self, fixture_name, expected_snippet):
        """FR-1.1, AC-001, AC-003: Negative fixtures fail with the expected boundary error."""
        path = FIXTURES_DIR / fixture_name
        assert path.is_file(), f"Fixture missing: {path}"
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)

        issues = validate_catalog(data, str(RM_SCHEMA_PATH))
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        assert errors, f"Fixture '{fixture_name}' was expected to fail validation"
        assert any(expected_snippet in e for e in errors), (
            f"Fixture '{fixture_name}' expected snippet '{expected_snippet}' in errors: {errors}"
        )

    def test_warning_os_version_fixture_produces_warning_without_error(self):
        """AC-003: Non-RHEL 10.0/10.2 valid OS version warns without blocking."""
        path = FIXTURES_DIR / "warning_os_version_catalog.json"
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)

        issues = validate_catalog(data, str(RM_SCHEMA_PATH))
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        warnings = [i["message"] for i in issues if i["severity"] == "warning"]

        assert not errors, f"Warning fixture produced unexpected errors: {errors}"
        assert any("only RHEL 10.0 and 10.2 are qualified" in w for w in warnings), (
            f"Expected OS qualification warning, got: {warnings}"
        )

    def test_all_bundled_standard_catalogs_backward_compatible(self):
        """AC-008: All existing bundled catalogs under src/main/samples/ remain valid."""
        bundled_catalogs = list(SAMPLES_DIR.rglob("*.json"))
        assert len(bundled_catalogs) > 0, f"No bundled catalogs found in {SAMPLES_DIR}"

        schema_path = str(RM_SCHEMA_PATH)
        for cat_file in bundled_catalogs:
            with open(cat_file, encoding="utf-8") as fh:
                data = json.load(fh)
            issues = validate_catalog(data, schema_path)
            errors = [i["message"] for i in issues if i["severity"] == "error"]
            assert not errors, f"Bundled catalog '{cat_file.name}' failed: {errors}"

    def test_image_build_manager_parse_catalog_compatibility(self):
        """FR-3.1, AC-004: IBM parse_catalog filters and resolves flexible layers."""
        parse_catalog_path = IBM_ROOT / "plugins" / "modules" / "parse_catalog.py"
        spec = importlib.util.spec_from_file_location("parse_catalog", parse_catalog_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        path = FIXTURES_DIR / "manual_valid_fg_catalog.json"
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)

        layers = data["catalog"]["functionallayer"]

        # Filter by x86_64
        x86_layers = module._filter_layers_by_arch(layers, "x86_64")
        x86_names = [l["name"] for l in x86_layers]
        assert "fg_webserver_rhel_10_2_x86_64" in x86_names
        assert "fg_database_rhel_10_2_x86_64" in x86_names
        assert "fg_compute_worker_rhel_10_0_aarch64" not in x86_names

        # Filter by aarch64
        aarch64_layers = module._filter_layers_by_arch(layers, "aarch64")
        aarch64_names = [l["name"] for l in aarch64_layers]
        assert "fg_compute_worker_rhel_10_0_aarch64" in aarch64_names
        assert "fg_mpi_worker_rhel_10_0_aarch64" in aarch64_names
        assert "fg_webserver_rhel_10_2_x86_64" not in aarch64_names

    def test_flexible_catalog_layers_fallback_contract_compatibility(self):
        """FR-3.1, AC-004: All flexible layers in positive fixtures align with fallback contract."""
        status_path = (
            REPO_ROOT
            / "test"
            / "fixtures"
            / "build_status"
            / "flexible_groups"
            / "valid_flexible_build_status.yml"
        )
        with open(status_path, encoding="utf-8") as fh:
            status_data = yaml.safe_load(fh)

        # Verify x86_64 and aarch64 entries resolve with complete artifacts
        usable, art, err = resolve_boot_image_fallback(
            status_data, "fg_webserver_rhel_10_0_x86_64", "x86_64"
        )
        assert usable is True, f"Failed fallback resolution: {err}"
        assert art["kernel"] and art["initrd"] and art["rootfs"]

        usable, art, err = resolve_boot_image_fallback(
            status_data, "fg_ai_worker_rhel_10_2_aarch64", "aarch64"
        )
        assert usable is True, f"Failed fallback resolution: {err}"
        assert art["kernel"] and art["initrd"] and art["rootfs"]
