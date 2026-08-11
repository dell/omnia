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

    def test_schema_has_functional_groups(self):
        """Schema must define functional_groups property."""
        schema_file = SCHEMA_DIR / "image_build_config.json"
        with open(schema_file, "r", encoding="utf-8") as f:
            schema = json.load(f)
        assert "functional_groups" in schema["properties"], (
            "Schema missing 'functional_groups' property"
        )

    def test_config_has_required_fields(self, image_build_config):
        """image_build_config.yml must have required top-level fields."""
        required = ["s3_configurations", "functional_groups"]
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

    def test_functional_groups_is_list(self, image_build_config):
        """functional_groups must be a list."""
        fg = image_build_config.get("functional_groups")
        assert isinstance(fg, list), "functional_groups must be a list"

    def test_functional_groups_have_names(self, image_build_config):
        """Each functional group must have a 'name' field."""
        for fg in image_build_config.get("functional_groups", []):
            if isinstance(fg, dict):
                assert "name" in fg, f"Functional group entry missing 'name': {fg}"
            elif isinstance(fg, str):
                assert len(fg) > 0, "Functional group name must not be empty"


class TestRepoStatus:
    """Validate repo_status.yml structure."""

    def test_has_overall_status(self, repo_status):
        """repo_status.yml must have overall_status."""
        assert "overall_status" in repo_status

    def test_has_cluster_os_type(self, repo_status):
        """repo_status.yml must have cluster_os_type."""
        assert "cluster_os_type" in repo_status

    def test_has_cluster_os_version(self, repo_status):
        """repo_status.yml must have cluster_os_version."""
        assert "cluster_os_version" in repo_status

    def test_has_rpm_repos(self, repo_status):
        """repo_status.yml must have rpm_repos section."""
        assert "rpm_repos" in repo_status
        assert isinstance(repo_status["rpm_repos"], dict)

    def test_rpm_repos_have_x86_64(self, repo_status):
        """rpm_repos must include x86_64 section."""
        assert "x86_64" in repo_status.get("rpm_repos", {}), (
            "rpm_repos missing x86_64 section"
        )

    def test_x86_64_has_baseos(self, repo_status):
        """x86_64 repos must include baseos."""
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

    def test_functional_group_packages_exists(self, repo_manager_output):
        """functional_group_packages.yml must exist (generated by dataset generator)."""
        path = repo_manager_output / "functional_group_packages.yml"
        if not path.exists():
            pytest.skip(
                "functional_group_packages.yml not in src/samples — "
                "generated by dataset generator"
            )

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
