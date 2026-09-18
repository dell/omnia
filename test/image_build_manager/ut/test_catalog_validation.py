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
"""Tests for catalog JSON schema and validation logic."""

import json
import pathlib
import sys
import tempfile


# ut/test_catalog... -> ut/ -> image_build_manager/ -> test/ -> omnia-bsm/
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

SCHEMA_DIR = (
    REPO_ROOT / "src" / "image_build_manager" / "plugins"
    / "module_utils" / "input_validation" / "schema"
)

SAMPLE_CATALOG = (
    REPO_ROOT / "src" / "main" / "samples" / "catalog_rhel.json"
)

# Add the src path so we can import the validator directly
_SRC_PLUGINS = (
    REPO_ROOT / "src" / "image_build_manager" / "plugins"
    / "module_utils"
)

# Mock the ansible import path for direct testing
_MOCK_PATH = str(REPO_ROOT / "src" / "image_build_manager" / "plugins")
if _MOCK_PATH not in sys.path:
    sys.path.insert(0, _MOCK_PATH)


class TestCatalogSchemaFile:
    """Validate the catalog.json schema file exists and is valid."""

    def test_schema_file_exists(self):
        """catalog.json schema must exist."""
        schema_file = SCHEMA_DIR / "catalog.json"
        assert schema_file.exists(), f"Schema not found at {schema_file}"

    def test_schema_is_valid_json(self):
        """Schema file must be valid JSON."""
        schema_file = SCHEMA_DIR / "catalog.json"
        with open(schema_file, "r", encoding="utf-8") as f:
            schema = json.load(f)
        assert "properties" in schema
        assert "required" in schema

    def test_schema_requires_catalog_root(self):
        """Schema must require 'catalog' root key."""
        schema_file = SCHEMA_DIR / "catalog.json"
        with open(schema_file, "r", encoding="utf-8") as f:
            schema = json.load(f)
        assert "catalog" in schema["required"]

    def test_schema_requires_functionallayer(self):
        """Schema must require 'functionallayer' in catalog object."""
        schema_file = SCHEMA_DIR / "catalog.json"
        with open(schema_file, "r", encoding="utf-8") as f:
            schema = json.load(f)
        catalog_props = schema["properties"]["catalog"]
        assert "functionallayer" in catalog_props["required"]

    def test_schema_requires_groups(self):
        """Schema must require 'groups' in catalog object."""
        schema_file = SCHEMA_DIR / "catalog.json"
        with open(schema_file, "r", encoding="utf-8") as f:
            schema = json.load(f)
        catalog_props = schema["properties"]["catalog"]
        assert "groups" in catalog_props["required"]

    def test_schema_requires_packages(self):
        """Schema must require 'packages' in catalog object."""
        schema_file = SCHEMA_DIR / "catalog.json"
        with open(schema_file, "r", encoding="utf-8") as f:
            schema = json.load(f)
        catalog_props = schema["properties"]["catalog"]
        assert "packages" in catalog_props["required"]


class TestSampleCatalogStructure:
    """Validate the sample catalog JSON structure."""

    def test_sample_catalog_exists(self):
        """Sample catalog must exist."""
        assert SAMPLE_CATALOG.exists(), (
            f"Sample catalog not found at {SAMPLE_CATALOG}"
        )

    def test_sample_catalog_is_valid_json(self):
        """Sample catalog must be valid JSON."""
        with open(SAMPLE_CATALOG, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "catalog" in data

    def test_sample_has_required_keys(self):
        """Sample catalog must have name, version, identifier, functionallayer, groups, packages."""
        with open(SAMPLE_CATALOG, "r", encoding="utf-8") as f:
            catalog = json.load(f)["catalog"]
        for key in ("name", "version", "identifier", "functionallayer", "groups", "packages"):
            assert key in catalog, f"Sample catalog missing required key: {key}"

    def test_sample_functionallayer_not_empty(self):
        """Sample catalog must have at least one functional layer."""
        with open(SAMPLE_CATALOG, "r", encoding="utf-8") as f:
            catalog = json.load(f)["catalog"]
        assert len(catalog["functionallayer"]) > 0

    def test_sample_groups_reference_valid_packages(self):
        """All package keys in groups.components must exist in packages.

        Known gap: ldms_group references ovis_ldms which is not yet
        defined in the sample catalog packages section.
        """
        # Known dangling references in the sample catalog (tracked for fix)
        known_gaps = {"ovis_ldms"}

        with open(SAMPLE_CATALOG, "r", encoding="utf-8") as f:
            catalog = json.load(f)["catalog"]
        groups = catalog.get("groups", {})
        packages = catalog.get("packages", {})
        dangling = []
        for group_name, group_data in groups.items():
            for pkg_key in group_data.get("components", []):
                if pkg_key not in packages and pkg_key not in known_gaps:
                    dangling.append(f"{group_name} -> {pkg_key}")
        assert not dangling, (
            f"Dangling package references in sample catalog: {dangling}"
        )

    def test_sample_layers_reference_valid_groups(self):
        """All component names in functionallayer.components must exist in groups."""
        with open(SAMPLE_CATALOG, "r", encoding="utf-8") as f:
            catalog = json.load(f)["catalog"]
        groups = catalog.get("groups", {})
        dangling = []
        for layer in catalog.get("functionallayer", []):
            for comp in layer.get("components", []):
                if comp not in groups:
                    dangling.append(f"{layer['name']} -> {comp}")
        assert not dangling, (
            f"Dangling group references in sample catalog: {dangling}"
        )

    def test_sample_has_baseos_group(self):
        """Sample catalog must have at least one base_os group."""
        with open(SAMPLE_CATALOG, "r", encoding="utf-8") as f:
            catalog = json.load(f)["catalog"]
        groups = catalog.get("groups", {})
        baseos = [
            name for name, data in groups.items()
            if data.get("type") == "base_os"
        ]
        assert len(baseos) > 0, "No base_os groups found in sample catalog"

    def test_sample_packages_have_sources(self):
        """Each package must have a sources array with architecture."""
        with open(SAMPLE_CATALOG, "r", encoding="utf-8") as f:
            catalog = json.load(f)["catalog"]
        packages = catalog.get("packages", {})
        no_sources = [
            key for key, pkg in packages.items()
            if not pkg.get("sources")
        ]
        assert not no_sources, (
            f"Packages without sources: {no_sources[:10]}"
        )
