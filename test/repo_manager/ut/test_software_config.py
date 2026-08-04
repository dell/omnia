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
"""Tests for software_config.json schema and content validation.

Validates that software_config.json conforms to the actual JSON schema at
src/repo_manager/plugins/module_utils/input_validation/schema/software_config.json.

Schema summary (software_config.json):
  Required top-level fields:
    - cluster_os_type  : string, enum ["rhel"]
    - cluster_os_version: string
    - repo_config      : string, enum ["always", "partial", "never"]
    - softwares        : array of software objects

  Each softwares item:
    Required: name (string), arch (array of strings, enum ["x86_64", "aarch64"],
              minItems 1, uniqueItems true)
    Optional: version (string)
    additionalProperties: false

  Optional top-level arrays (each item requires "name"):
    additional_software, bcm_roce, amdgpu, pytorch, tensorflow, intelgaudi
"""

import jsonschema
import pytest


# ---------------------------------------------------------------------------
# Schema file tests
# ---------------------------------------------------------------------------
class TestSoftwareConfigSchemaFile:
    """Validate the schema file itself is well-formed."""

    def test_schema_file_exists(self, schema_dir):
        """software_config.json schema file must exist."""
        assert (schema_dir / "software_config.json").exists()

    def test_schema_is_valid_json(self, software_config_schema):
        """Schema must be parseable JSON with expected top-level keys."""
        assert "properties" in software_config_schema
        assert "type" in software_config_schema
        assert software_config_schema["type"] == "object"

    def test_schema_declares_required_fields(self, software_config_schema):
        """Schema must declare the four required fields."""
        required = software_config_schema.get("required", [])
        for field in ["cluster_os_type", "cluster_os_version", "repo_config", "softwares"]:
            assert field in required, (
                f"Schema 'required' missing '{field}'"
            )

    def test_schema_cluster_os_type_enum(self, software_config_schema):
        """cluster_os_type must be an enum with 'rhel'."""
        prop = software_config_schema["properties"]["cluster_os_type"]
        assert prop["type"] == "string"
        assert prop["enum"] == ["rhel"]

    def test_schema_repo_config_enum(self, software_config_schema):
        """repo_config must be an enum with 'always', 'partial', 'never'."""
        prop = software_config_schema["properties"]["repo_config"]
        assert prop["type"] == "string"
        assert set(prop["enum"]) == {"always", "partial", "never"}

    def test_schema_softwares_items_required(self, software_config_schema):
        """Each software item must require 'name' and 'arch'."""
        items = software_config_schema["properties"]["softwares"]["items"]
        assert "name" in items["required"]
        assert "arch" in items["required"]

    def test_schema_softwares_arch_enum(self, software_config_schema):
        """arch items must be enum of ['x86_64', 'aarch64']."""
        arch_schema = software_config_schema["properties"]["softwares"]["items"]["properties"]["arch"]
        assert arch_schema["type"] == "array"
        assert set(arch_schema["items"]["enum"]) == {"x86_64", "aarch64"}
        assert arch_schema["minItems"] == 1
        assert arch_schema["uniqueItems"] is True

    def test_schema_softwares_no_additional_properties(self, software_config_schema):
        """Software items must not allow additionalProperties."""
        items = software_config_schema["properties"]["softwares"]["items"]
        assert items.get("additionalProperties") is False

    def test_schema_version_is_optional_string(self, software_config_schema):
        """version field in software items must be an optional string."""
        items = software_config_schema["properties"]["softwares"]["items"]
        assert "version" in items["properties"]
        assert items["properties"]["version"]["type"] == "string"
        assert "version" not in items["required"]


# ---------------------------------------------------------------------------
# Default input file structure tests
# ---------------------------------------------------------------------------
class TestSoftwareConfigStructure:
    """Validate the structure of the default software_config.json input file."""

    def test_has_cluster_os_type(self, software_config):
        """software_config.json must have cluster_os_type."""
        assert "cluster_os_type" in software_config, (
            "software_config.json missing 'cluster_os_type'"
        )

    def test_cluster_os_type_is_rhel(self, software_config):
        """cluster_os_type must be 'rhel' (the only allowed value)."""
        assert software_config["cluster_os_type"] == "rhel"

    def test_has_cluster_os_version(self, software_config):
        """software_config.json must have cluster_os_version."""
        assert "cluster_os_version" in software_config
        assert isinstance(software_config["cluster_os_version"], str)

    def test_has_repo_config(self, software_config):
        """software_config.json must have repo_config."""
        assert "repo_config" in software_config

    def test_repo_config_is_valid_enum(self, software_config):
        """repo_config must be one of 'always', 'partial', or 'never'."""
        assert software_config["repo_config"] in ("always", "partial", "never"), (
            f"Invalid repo_config value: {software_config['repo_config']}"
        )

    def test_has_softwares(self, software_config):
        """software_config.json must have softwares."""
        assert "softwares" in software_config

    def test_softwares_is_list(self, software_config):
        """softwares must be a list."""
        assert isinstance(software_config["softwares"], list)

    def test_softwares_not_empty(self, software_config):
        """softwares list must not be empty."""
        assert len(software_config["softwares"]) > 0

    def test_each_software_has_name(self, software_config):
        """Each software entry must have a 'name' field (string)."""
        for entry in software_config["softwares"]:
            assert "name" in entry, f"Software entry missing 'name': {entry}"
            assert isinstance(entry["name"], str)

    def test_each_software_has_arch(self, software_config):
        """Each software entry must have an 'arch' field (array of strings)."""
        for entry in software_config["softwares"]:
            assert "arch" in entry, f"Software entry missing 'arch': {entry}"
            assert isinstance(entry["arch"], list)
            assert len(entry["arch"]) >= 1, (
                f"Software '{entry['name']}' has empty arch list"
            )

    def test_arch_values_are_valid(self, software_config):
        """All arch values must be 'x86_64' or 'aarch64'."""
        valid_arches = {"x86_64", "aarch64"}
        for entry in software_config["softwares"]:
            for arch in entry.get("arch", []):
                assert arch in valid_arches, (
                    f"Software '{entry['name']}' has invalid arch '{arch}'"
                )

    def test_arch_values_are_unique(self, software_config):
        """Each software entry must not have duplicate arch values."""
        for entry in software_config["softwares"]:
            arches = entry.get("arch", [])
            assert len(arches) == len(set(arches)), (
                f"Software '{entry['name']}' has duplicate arch values"
            )

    def test_version_is_string_when_present(self, software_config):
        """Version field, if present, must be a string."""
        for entry in software_config["softwares"]:
            if "version" in entry:
                assert isinstance(entry["version"], str), (
                    f"Software '{entry['name']}' has non-string version"
                )

    def test_default_packages_present(self, software_config):
        """softwares must include a 'default_packages' entry."""
        names = [s["name"] for s in software_config["softwares"]]
        assert "default_packages" in names, (
            "softwares missing 'default_packages' entry"
        )


# ---------------------------------------------------------------------------
# JSON schema validation tests (positive and negative)
# ---------------------------------------------------------------------------
class TestSoftwareConfigSchemaValidation:
    """Validate data against the actual JSON schema using jsonschema."""

    def test_default_config_validates(self, software_config, software_config_schema):
        """The default software_config.json must validate against the schema."""
        jsonschema.validate(instance=software_config, schema=software_config_schema)

    def test_minimal_valid_config(self, software_config_schema):
        """A minimal valid config must pass schema validation."""
        minimal = {
            "cluster_os_type": "rhel",
            "cluster_os_version": "10.0",
            "repo_config": "always",
            "softwares": [
                {"name": "default_packages", "arch": ["x86_64"]}
            ],
        }
        jsonschema.validate(instance=minimal, schema=software_config_schema)

    def test_software_with_version(self, software_config_schema):
        """A software entry with version must pass validation."""
        data = {
            "cluster_os_type": "rhel",
            "cluster_os_version": "10.0",
            "repo_config": "partial",
            "softwares": [
                {"name": "service_k8s", "version": "1.35.1", "arch": ["x86_64"]}
            ],
        }
        jsonschema.validate(instance=data, schema=software_config_schema)

    def test_software_with_both_arches(self, software_config_schema):
        """A software entry with both architectures must pass validation."""
        data = {
            "cluster_os_type": "rhel",
            "cluster_os_version": "10.0",
            "repo_config": "never",
            "softwares": [
                {"name": "default_packages", "arch": ["x86_64", "aarch64"]}
            ],
        }
        jsonschema.validate(instance=data, schema=software_config_schema)

    def test_missing_cluster_os_type_fails(self, software_config_schema):
        """Missing cluster_os_type must fail validation."""
        data = {
            "cluster_os_version": "10.0",
            "repo_config": "always",
            "softwares": [{"name": "pkg", "arch": ["x86_64"]}],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=software_config_schema)

    def test_missing_cluster_os_version_fails(self, software_config_schema):
        """Missing cluster_os_version must fail validation."""
        data = {
            "cluster_os_type": "rhel",
            "repo_config": "always",
            "softwares": [{"name": "pkg", "arch": ["x86_64"]}],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=software_config_schema)

    def test_missing_repo_config_fails(self, software_config_schema):
        """Missing repo_config must fail validation."""
        data = {
            "cluster_os_type": "rhel",
            "cluster_os_version": "10.0",
            "softwares": [{"name": "pkg", "arch": ["x86_64"]}],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=software_config_schema)

    def test_missing_softwares_fails(self, software_config_schema):
        """Missing softwares must fail validation."""
        data = {
            "cluster_os_type": "rhel",
            "cluster_os_version": "10.0",
            "repo_config": "always",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=software_config_schema)

    def test_invalid_cluster_os_type_fails(self, software_config_schema):
        """Invalid cluster_os_type (not 'rhel') must fail validation."""
        data = {
            "cluster_os_type": "ubuntu",
            "cluster_os_version": "22.04",
            "repo_config": "always",
            "softwares": [{"name": "pkg", "arch": ["x86_64"]}],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=software_config_schema)

    def test_invalid_repo_config_fails(self, software_config_schema):
        """Invalid repo_config value must fail validation."""
        data = {
            "cluster_os_type": "rhel",
            "cluster_os_version": "10.0",
            "repo_config": "sometimes",
            "softwares": [{"name": "pkg", "arch": ["x86_64"]}],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=software_config_schema)

    def test_software_missing_name_fails(self, software_config_schema):
        """A software entry without 'name' must fail validation."""
        data = {
            "cluster_os_type": "rhel",
            "cluster_os_version": "10.0",
            "repo_config": "always",
            "softwares": [{"arch": ["x86_64"]}],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=software_config_schema)

    def test_software_missing_arch_fails(self, software_config_schema):
        """A software entry without 'arch' must fail validation."""
        data = {
            "cluster_os_type": "rhel",
            "cluster_os_version": "10.0",
            "repo_config": "always",
            "softwares": [{"name": "pkg"}],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=software_config_schema)

    def test_software_empty_arch_fails(self, software_config_schema):
        """A software entry with empty arch array must fail (minItems: 1)."""
        data = {
            "cluster_os_type": "rhel",
            "cluster_os_version": "10.0",
            "repo_config": "always",
            "softwares": [{"name": "pkg", "arch": []}],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=software_config_schema)

    def test_software_invalid_arch_fails(self, software_config_schema):
        """A software entry with invalid arch value must fail."""
        data = {
            "cluster_os_type": "rhel",
            "cluster_os_version": "10.0",
            "repo_config": "always",
            "softwares": [{"name": "pkg", "arch": ["arm32"]}],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=software_config_schema)

    def test_software_duplicate_arch_fails(self, software_config_schema):
        """A software entry with duplicate arch values must fail (uniqueItems)."""
        data = {
            "cluster_os_type": "rhel",
            "cluster_os_version": "10.0",
            "repo_config": "always",
            "softwares": [{"name": "pkg", "arch": ["x86_64", "x86_64"]}],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=software_config_schema)

    def test_software_extra_property_fails(self, software_config_schema):
        """A software entry with extra properties must fail (additionalProperties: false)."""
        data = {
            "cluster_os_type": "rhel",
            "cluster_os_version": "10.0",
            "repo_config": "always",
            "softwares": [
                {"name": "pkg", "arch": ["x86_64"], "unknown_field": "value"}
            ],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=software_config_schema)

    def test_softwares_not_array_fails(self, software_config_schema):
        """softwares must be an array, not a string."""
        data = {
            "cluster_os_type": "rhel",
            "cluster_os_version": "10.0",
            "repo_config": "always",
            "softwares": "not_an_array",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=software_config_schema)

    def test_cluster_os_version_must_be_string(self, software_config_schema):
        """cluster_os_version must be a string, not a number."""
        data = {
            "cluster_os_type": "rhel",
            "cluster_os_version": 10.0,
            "repo_config": "always",
            "softwares": [{"name": "pkg", "arch": ["x86_64"]}],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=software_config_schema)
