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

"""Unit tests for get_package_list function in generator module."""

import json
import os
import sys
import tempfile
import unittest

from jsonschema import ValidationError

HERE = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))  # Go up 5 levels to reach build_stream root
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.catalog.generator import (
    FeatureList,
    serialize_json,
    get_package_list,
)


class TestGetPackageList(unittest.TestCase):
    """Tests for get_package_list function."""

    def setUp(self):
        """Set up test fixtures."""
        self.base_dir = os.path.dirname(__file__)
        # Calculate path to fixtures: tests/integration/core/catalog -> tests/fixtures/catalogs
        self.fixture_path = os.path.abspath(
            os.path.join(self.base_dir, "..", "..", "..", "fixtures", "catalogs", "functional_layer.json")
        )

    def test_get_packages_for_valid_single_role(self):
        """TC01: Given a valid role, returns list with one role object containing packages."""
        result = get_package_list(self.fixture_path, role="Compiler")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["roleName"], "Compiler")
        self.assertIn("packages", result[0])
        self.assertIsInstance(result[0]["packages"], list)
        self.assertGreater(len(result[0]["packages"]), 0)

    def test_get_packages_for_all_roles_when_role_is_none(self):
        """TC02: When role is None, returns list with all role objects."""
        result = get_package_list(self.fixture_path, role=None)

        self.assertIsInstance(result, list)
        # Fixture has 6 roles
        expected_roles = [
            "Compiler",
            "K8S Controller",
            "K8S Worker",
            "Login Node",
            "Slurm Controller",
            "Slurm Worker",
        ]
        actual_roles = [r["roleName"] for r in result]
        self.assertCountEqual(actual_roles, expected_roles)

    def test_invalid_role_raises_value_error(self):
        """TC03: Invalid/unknown role raises ValueError with clear message."""
        with self.assertRaises(ValueError) as context:
            get_package_list(self.fixture_path, role="NonExistentRole")

        self.assertIn("NonExistentRole", str(context.exception))

    def test_empty_role_raises_value_error(self):
        """Empty role string is treated as invalid input."""
        with self.assertRaises(ValueError) as context:
            get_package_list(self.fixture_path, role="")

        self.assertIn("non-empty", str(context.exception))

    def test_file_not_found_raises_error(self):
        """TC04: Non-existent file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            get_package_list("/nonexistent/path/functional_layer.json")

    def test_malformed_json_raises_error(self):
        """TC05: Malformed JSON raises json.JSONDecodeError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            malformed_path = os.path.join(tmp_dir, "malformed.json")
            with open(malformed_path, "w", encoding="utf-8") as f:
                f.write("{ invalid json }")

            with self.assertRaises(json.JSONDecodeError):
                get_package_list(malformed_path)

    def test_schema_validation_failure_raises_error(self):
        """TC06: JSON that fails schema validation raises ValidationError."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Missing required 'architecture' field for a package item
            invalid_json = {
                "SomeRole": {
                    "packages": [
                        {
                            "package": "firewalld",
                            "type": "rpm",
                            "repo_name": "x86_64_baseos",
                            # Missing 'architecture' field
                        }
                    ]
                }
            }
            json_path = os.path.join(tmp_dir, "invalid_schema.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(invalid_json, f)

            with self.assertRaises(ValidationError):
                get_package_list(json_path)

    def test_empty_feature_list_returns_empty_list(self):
        """TC07: Empty feature list returns empty list."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_feature_list = FeatureList(features={})
            json_path = os.path.join(tmp_dir, "empty_functional_layer.json")
            serialize_json(empty_feature_list, json_path)

            result = get_package_list(json_path)

            self.assertEqual(result, [])

    def test_package_attributes_are_complete(self):
        """TC08: All package fields are present in the response."""
        result = get_package_list(self.fixture_path, role="Compiler")

        self.assertEqual(len(result), 1)
        packages = result[0]["packages"]
        self.assertGreater(len(packages), 0)

        # Check first package has all required fields
        first_pkg = packages[0]
        required_fields = ["name", "type", "repo_name", "architecture", "uri", "tag"]
        for field in required_fields:
            self.assertIn(field, first_pkg, f"Missing field: {field}")

    def test_package_with_uri_and_tag(self):
        """Verify packages with uri and tag fields are correctly returned."""
        result = get_package_list(self.fixture_path, role="K8S Controller")

        packages = result[0]["packages"]
        # Find a package with tag (image type)
        image_pkgs = [p for p in packages if p["type"] == "image"]
        self.assertGreater(len(image_pkgs), 0)
        # Image packages should have tag
        self.assertIsNotNone(image_pkgs[0].get("tag"))

        # Find a package with uri (tarball type)
        tarball_pkgs = [p for p in packages if p["type"] == "tarball"]
        self.assertGreater(len(tarball_pkgs), 0)
        # Tarball packages should have uri
        self.assertIsNotNone(tarball_pkgs[0].get("uri"))

    def test_role_with_spaces_in_name(self):
        """Verify roles with spaces in name work correctly."""
        result = get_package_list(self.fixture_path, role="K8S Controller")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["roleName"], "K8S Controller")

    def test_all_roles_returns_correct_package_counts(self):
        """Verify each role returns the correct number of packages."""
        result = get_package_list(self.fixture_path, role=None)

        # Verify we have packages for each role
        for role_obj in result:
            self.assertIn("roleName", role_obj)
            self.assertIn("packages", role_obj)
            # Each role should have at least one package
            self.assertGreater(
                len(role_obj["packages"]),
                0,
                f"Role {role_obj['roleName']} has no packages",
            )

    def test_case_insensitive_role_matching_lowercase(self):
        """Verify role matching is case-insensitive with lowercase input."""
        result = get_package_list(self.fixture_path, role="compiler")

        self.assertEqual(len(result), 1)
        # Should return the original role name from JSON
        self.assertEqual(result[0]["roleName"], "Compiler")

    def test_case_insensitive_role_matching_uppercase(self):
        """Verify role matching is case-insensitive with uppercase input."""
        result = get_package_list(self.fixture_path, role="COMPILER")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["roleName"], "Compiler")

    def test_case_insensitive_role_matching_mixed_case(self):
        """Verify role matching is case-insensitive with mixed case input."""
        result = get_package_list(self.fixture_path, role="k8s controller")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["roleName"], "K8S Controller")

    def test_case_insensitive_role_matching_preserves_original_name(self):
        """Verify the returned roleName preserves the original case from JSON."""
        result = get_package_list(self.fixture_path, role="SLURM CONTROLLER")

        self.assertEqual(len(result), 1)
        # Should preserve original case from JSON
        self.assertEqual(result[0]["roleName"], "Slurm Controller")


if __name__ == "__main__":
    unittest.main()
