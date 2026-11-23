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

"""Unit tests for Repo Manager catalog validation with flexible group fixtures."""

import json
import unittest

from source_loader import REPO_MANAGER_ROOT, REPOSITORY_ROOT
from ansible.module_utils.catalog.validator import validate_catalog

SCHEMA_PATH = str(REPO_MANAGER_ROOT / "schemas" / "catalog_schema.json")
FIXTURES_DIR = REPOSITORY_ROOT / "test" / "fixtures" / "catalogs" / "flexible_groups"


class FlexibleGroupCatalogFixturesTests(unittest.TestCase):
    """Test flexible group catalog validation across positive and negative fixtures."""

    def test_manual_valid_catalog_passes(self):
        """AC-001, AC-008: Valid catalog with up to 10 fg_ groups passes validation."""
        path = FIXTURES_DIR / "manual_valid_fg_catalog.json"
        cat = json.loads(path.read_text(encoding="utf-8"))
        issues = validate_catalog(cat, SCHEMA_PATH)
        errors = [i for i in issues if i["severity"] == "error"]
        self.assertEqual(errors, [])

    def test_reviewed_generated_catalog_passes(self):
        """FR-1.1, ER-BSM-001: Operator-reviewed generated catalog passes validation."""
        path = FIXTURES_DIR / "reviewed_generated_fg_catalog.json"
        cat = json.loads(path.read_text(encoding="utf-8"))
        issues = validate_catalog(cat, SCHEMA_PATH)
        errors = [i for i in issues if i["severity"] == "error"]
        self.assertEqual(errors, [])

    def test_missing_fg_prefix_rejected(self):
        """FR-1.1: Non-predefined layer missing fg_ prefix fails validation."""
        path = FIXTURES_DIR / "invalid_missing_prefix_catalog.json"
        cat = json.loads(path.read_text(encoding="utf-8"))
        issues = validate_catalog(cat, SCHEMA_PATH)
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        self.assertTrue(any("mandatory 'fg_' prefix" in e for e in errors))

    def test_count_boundary_exceeded_rejected(self):
        """AC-001: More than 10 flexible groups in catalog fails validation."""
        path = FIXTURES_DIR / "invalid_count_exceeded_catalog.json"
        cat = json.loads(path.read_text(encoding="utf-8"))
        issues = validate_catalog(cat, SCHEMA_PATH)
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        self.assertTrue(any("maximum allowed is 10" in e for e in errors))

    def test_missing_suffix_rejected(self):
        """FR-1.1: Flexible group missing platform suffix fails validation."""
        path = FIXTURES_DIR / "invalid_suffix_missing_catalog.json"
        cat = json.loads(path.read_text(encoding="utf-8"))
        issues = validate_catalog(cat, SCHEMA_PATH)
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        self.assertTrue(any("platform suffix" in e for e in errors))

    def test_unsupported_architecture_rejected(self):
        """AC-001, AC-003: Unsupported architecture (ppc64le) fails validation."""
        path = FIXTURES_DIR / "invalid_architecture_catalog.json"
        cat = json.loads(path.read_text(encoding="utf-8"))
        issues = validate_catalog(cat, SCHEMA_PATH)
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        self.assertTrue(any("unsupported architecture 'ppc64le'" in e for e in errors))

    def test_unreviewed_generated_catalog_rejected(self):
        """FR-1.1, ER-BSM-001: Unreviewed generated catalog fails validation."""
        path = FIXTURES_DIR / "unreviewed_generated_catalog.json"
        cat = json.loads(path.read_text(encoding="utf-8"))
        issues = validate_catalog(cat, SCHEMA_PATH)
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        self.assertTrue(any("operator review approval" in e for e in errors))

    def test_warning_os_version_produces_warning_not_error(self):
        """AC-003: Unqualified OS (rocky 10.2) warns without blocking."""
        path = FIXTURES_DIR / "warning_os_version_catalog.json"
        cat = json.loads(path.read_text(encoding="utf-8"))
        issues = validate_catalog(cat, SCHEMA_PATH)
        errors = [i for i in issues if i["severity"] == "error"]
        warnings = [i["message"] for i in issues if i["severity"] == "warning"]
        self.assertEqual(errors, [])
        self.assertTrue(any("only RHEL 10.0 and 10.2 are qualified" in w for w in warnings))

    def test_referential_integrity_broken_group(self):
        """FR-1.1: Missing group reference fails validation."""
        path = FIXTURES_DIR / "broken_referential_group_catalog.json"
        cat = json.loads(path.read_text(encoding="utf-8"))
        issues = validate_catalog(cat, SCHEMA_PATH)
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        self.assertTrue(any("references missing group" in e for e in errors))

    def test_referential_integrity_broken_package(self):
        """FR-1.1: Missing package reference fails validation."""
        path = FIXTURES_DIR / "broken_referential_package_catalog.json"
        cat = json.loads(path.read_text(encoding="utf-8"))
        issues = validate_catalog(cat, SCHEMA_PATH)
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        self.assertTrue(any("references missing package" in e for e in errors))

    def test_baseos_group_missing(self):
        """FR-1.1: Missing baseos group fails validation."""
        path = FIXTURES_DIR / "broken_baseos_catalog.json"
        cat = json.loads(path.read_text(encoding="utf-8"))
        issues = validate_catalog(cat, SCHEMA_PATH)
        errors = [i["message"] for i in issues if i["severity"] == "error"]
        self.assertTrue(any("must have exactly one baseos group" in e for e in errors))
