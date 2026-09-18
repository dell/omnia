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
"""Tests for image_build_config.yml schema and content validation."""

import json
import pathlib

import pytest
import yaml


# ut/test_validate_... -> ut/ -> image_build_manager/ -> test/ -> omnia-bsm/
SCHEMA_DIR = (
    pathlib.Path(__file__).resolve().parents[3]
    / "src"
    / "image_build_manager"
    / "plugins"
    / "module_utils"
    / "input_validation"
    / "schema"
)


class TestImageBuildConfigSchema:
    """Validate image_build_config.yml against its JSON schema."""

    def test_schema_file_exists(self):
        """JSON schema file must exist."""
        schema_file = SCHEMA_DIR / "image_build_config.json"
        assert schema_file.exists(), f"Schema not found at {schema_file}"

    def test_schema_is_valid_json(self):
        """Schema file must be valid JSON."""
        schema_file = SCHEMA_DIR / "image_build_config.json"
        with open(schema_file, "r", encoding="utf-8") as f:
            schema = json.load(f)
        assert "properties" in schema
        assert "type" in schema

    def test_schema_has_functional_groups_source(self):
        """Schema must define functional_groups_source property."""
        schema_file = SCHEMA_DIR / "image_build_config.json"
        with open(schema_file, "r", encoding="utf-8") as f:
            schema = json.load(f)
        assert "functional_groups_source" in schema["properties"], (
            "Schema missing 'functional_groups_source' property"
        )

    def test_config_has_required_fields(self, image_build_config):
        """image_build_config.yml must have required top-level fields."""
        required = ["s3_configurations", "functional_groups_source"]
        for field in required:
            assert field in image_build_config, (
                f"image_build_config.yml missing required field '{field}'"
            )

    def test_s3_provider_valid(self, image_build_config):
        """S3 provider must be 'minio' or 'powerscale'."""
        provider = image_build_config.get("s3_configurations", {}).get("provider")
        assert provider in ("minio", "powerscale"), (
            f"Invalid S3 provider: '{provider}'"
        )

    def test_functional_groups_source_valid(self, image_build_config):
        """functional_groups_source must be 'config' or 'catalog'."""
        fgs = image_build_config.get("functional_groups_source")
        assert fgs in ("config", "catalog"), (
            f"Invalid functional_groups_source: '{fgs}'"
        )


class TestRepoStatus:
    """Validate repo_status.yml structure (supports old and new formats)."""

    def test_has_overall_status(self, repo_status):
        """repo_status.yml must have overall_status."""
        assert "overall_status" in repo_status

    def test_has_cluster_os_type(self, repo_status):
        """repo_status.yml must have cluster_os_type."""
        assert "cluster_os_type" in repo_status

    def test_has_repositories_or_rpm_repos(self, repo_status):
        """repo_status.yml must have repositories (new) or rpm_repos (old)."""
        has_repos = "repositories" in repo_status or "rpm_repos" in repo_status
        assert has_repos, (
            "repo_status.yml must have 'repositories' (new format) "
            "or 'rpm_repos' (old format)"
        )

    def test_repositories_have_x86_64(self, repo_status):
        """Repositories must include x86_64 section."""
        if "repositories" in repo_status:
            # New format: repositories.{version}.{arch}
            for version, arches in repo_status["repositories"].items():
                if isinstance(arches, dict) and "x86_64" in arches:
                    return
            pytest.fail("repositories missing x86_64 section in any version")
        elif "rpm_repos" in repo_status:
            # Old format: rpm_repos.{arch}
            assert "x86_64" in repo_status["rpm_repos"], (
                "rpm_repos missing x86_64 section"
            )

    def test_x86_64_has_baseos(self, repo_status):
        """x86_64 repos must include baseos."""
        if "repositories" in repo_status:
            for version, arches in repo_status["repositories"].items():
                if isinstance(arches, dict):
                    x86 = arches.get("x86_64", {})
                    if "baseos" in x86:
                        return
            pytest.fail("repositories missing baseos for x86_64")
        elif "rpm_repos" in repo_status:
            x86 = repo_status.get("rpm_repos", {}).get("x86_64", {})
            assert "baseos" in x86, "x86_64 rpm_repos missing 'baseos'"


class TestInputFilesExist:
    """Validate that all required input files exist in the repo."""

    def test_image_build_config_exists(self, input_dir):
        """image_build_config.yml must exist."""
        assert (input_dir / "image_build_config.yml").exists()

    def test_repo_status_exists(self, repo_manager_output):
        """repo_status.yml must exist."""
        assert (repo_manager_output / "repo_status.yml").exists()

    def test_package_groups_exists(self, input_dir):
        """package_groups.yml must exist in input/ (functional group mapping)."""
        assert (input_dir / "package_groups.yml").exists()

    def test_certs_dir_exists(self, repo_manager_output):
        """certs/ directory must exist (generated by dataset generator)."""
        path = repo_manager_output / "certs"
        if not path.is_dir():
            pytest.skip(
                "certs/ not in src/samples — "
                "generated by dataset generator"
            )


class TestNoHardcodedOmniaPaths:
    """Ensure no active code has hardcoded /opt/omnia defaults."""

    def _scan_file(self, filepath):
        """Scan a file for uncommented /opt/omnia references."""
        issues = []
        with open(filepath, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if "/opt/omnia" in line and "default(" in line:
                    issues.append(f"{filepath}:{lineno}: {stripped}")
        return issues

    def test_role_vars_no_omnia_defaults(self, src_dir):
        """Role vars must not have /opt/omnia in default() expressions."""
        roles_dir = src_dir / "roles"
        issues = []
        for vars_file in roles_dir.rglob("vars/main.yml"):
            issues.extend(self._scan_file(vars_file))
        assert len(issues) == 0, (
            f"Found /opt/omnia default() in role vars:\n"
            + "\n".join(issues)
        )
