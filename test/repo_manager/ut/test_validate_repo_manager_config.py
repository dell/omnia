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
"""Tests for repo_manager_config.yml schema and content validation.

Validates that repo_manager_config.yml conforms to the actual JSON schema at:
  src/repo_manager/plugins/module_utils/input_validation/schema/
  repo_manager_config.json

Schema summary (repo_manager_config.json):
  Required fields:
    - omnia_repo_url_rhel_x86_64  : array|null of repo objects
    - omnia_repo_url_rhel_aarch64 : array|null of repo objects

  Optional fields (all array|null):
    - user_registry               : array of {host (required), cert_path, key_path}
    - user_repo_url_x86_64        : array of repo objects
    - user_repo_url_aarch64       : array of repo objects
    - rhel_os_url_x86_64          : array of repo objects
    - rhel_os_url_aarch64         : array of repo objects
    - additional_repos_x86_64     : array of repo objects
    - additional_repos_aarch64    : array of repo objects
    - rhel_subscription_repo_config_x86_64  : array of repo objects (url, name required)
    - rhel_subscription_repo_config_aarch64 : array of repo objects (url, name required)

  Repo objects (omnia_repo_url, user_repo_url, rhel_os_url, additional_repos):
    Required: url (string, http/https pattern), gpgkey (string), name (string)
    Optional: policy (enum), sslcacert, sslclientkey, sslclientcert

  additionalProperties: false
"""

import jsonschema
import pytest


# ---------------------------------------------------------------------------
# Schema file tests
# ---------------------------------------------------------------------------
class TestRepoManagerConfigSchemaFile:
    """Validate the repo_manager_config schema file itself."""

    def test_schema_file_exists(self, schema_dir):
        """repo_manager_config.json schema file must exist."""
        assert (schema_dir / "repo_manager_config.json").exists()

    def test_schema_is_valid_json(self, repo_manager_config_schema):
        """Schema must be parseable JSON with expected top-level keys."""
        assert "properties" in repo_manager_config_schema
        assert "type" in repo_manager_config_schema
        assert repo_manager_config_schema["type"] == "object"

    def test_schema_declares_required_fields(self, repo_manager_config_schema):
        """Schema must declare the two required fields."""
        required = repo_manager_config_schema.get("required", [])
        assert "omnia_repo_url_rhel_x86_64" in required
        assert "omnia_repo_url_rhel_aarch64" in required

    def test_schema_disallows_additional_properties(self, repo_manager_config_schema):
        """Schema must set additionalProperties to false."""
        assert repo_manager_config_schema.get("additionalProperties") is False

    def test_schema_has_all_expected_properties(self, repo_manager_config_schema):
        """Schema must define all expected top-level properties."""
        expected_props = [
            "omnia_repo_url_rhel_x86_64",
            "omnia_repo_url_rhel_aarch64",
            "user_registry",
            "user_repo_url_x86_64",
            "user_repo_url_aarch64",
            "rhel_os_url_x86_64",
            "rhel_os_url_aarch64",
            "additional_repos_x86_64",
            "additional_repos_aarch64",
            "rhel_subscription_repo_config_x86_64",
            "rhel_subscription_repo_config_aarch64",
        ]
        props = repo_manager_config_schema["properties"]
        for prop_name in expected_props:
            assert prop_name in props, (
                f"Schema missing expected property '{prop_name}'"
            )

    def test_schema_omnia_repo_url_type(self, repo_manager_config_schema):
        """omnia_repo_url fields must allow array or null."""
        for key in ["omnia_repo_url_rhel_x86_64", "omnia_repo_url_rhel_aarch64"]:
            prop = repo_manager_config_schema["properties"][key]
            assert "array" in prop["type"]
            assert "null" in prop["type"]

    def test_schema_omnia_repo_url_item_required_fields(self, repo_manager_config_schema):
        """omnia_repo_url items must require url, gpgkey, and name."""
        for key in ["omnia_repo_url_rhel_x86_64", "omnia_repo_url_rhel_aarch64"]:
            items = repo_manager_config_schema["properties"][key]["items"]
            assert "url" in items["required"]
            assert "gpgkey" in items["required"]
            assert "name" in items["required"]

    def test_schema_user_registry_host_required(self, repo_manager_config_schema):
        """user_registry items must require 'host'."""
        items = repo_manager_config_schema["properties"]["user_registry"]["items"]
        assert "host" in items["required"]
        assert "host" in items["properties"]

    def test_schema_user_registry_host_pattern(self, repo_manager_config_schema):
        """user_registry host must have IP:port pattern."""
        host_prop = (
            repo_manager_config_schema["properties"]["user_registry"]["items"]
            ["properties"]["host"]
        )
        assert "pattern" in host_prop

    def test_schema_optional_arrays_allow_null(self, repo_manager_config_schema):
        """Optional array fields must allow null."""
        optional_arrays = [
            "user_registry",
            "user_repo_url_x86_64",
            "user_repo_url_aarch64",
            "rhel_os_url_x86_64",
            "rhel_os_url_aarch64",
            "additional_repos_x86_64",
            "additional_repos_aarch64",
        ]
        for key in optional_arrays:
            prop = repo_manager_config_schema["properties"][key]
            assert "null" in prop["type"], (
                f"Property '{key}' must allow null type"
            )


# ---------------------------------------------------------------------------
# Default input file structure tests
# ---------------------------------------------------------------------------
class TestRepoManagerConfigStructure:
    """Validate repo_manager_config.yml structure and content."""

    def test_config_loads_as_yaml(self, repo_manager_config):
        """repo_manager_config.yml must load as valid YAML."""
        assert repo_manager_config is not None, (
            "repo_manager_config.yml loaded as None (empty file)"
        )
        assert isinstance(repo_manager_config, dict), (
            "repo_manager_config.yml must load as a dict"
        )

    def test_omnia_repo_url_rhel_x86_64_present(self, repo_manager_config):
        """repo_manager_config.yml must have omnia_repo_url_rhel_x86_64."""
        assert "omnia_repo_url_rhel_x86_64" in repo_manager_config, (
            "repo_manager_config.yml missing 'omnia_repo_url_rhel_x86_64'"
        )

    def test_omnia_repo_url_rhel_aarch64_present(self, repo_manager_config):
        """repo_manager_config.yml must have omnia_repo_url_rhel_aarch64."""
        assert "omnia_repo_url_rhel_aarch64" in repo_manager_config, (
            "repo_manager_config.yml missing 'omnia_repo_url_rhel_aarch64'"
        )

    def test_omnia_repo_url_x86_64_is_list(self, repo_manager_config):
        """omnia_repo_url_rhel_x86_64 must be a list."""
        repos = repo_manager_config["omnia_repo_url_rhel_x86_64"]
        assert isinstance(repos, list), "omnia_repo_url_rhel_x86_64 must be a list"

    def test_omnia_repo_url_x86_64_not_empty(self, repo_manager_config):
        """omnia_repo_url_rhel_x86_64 must not be empty."""
        repos = repo_manager_config["omnia_repo_url_rhel_x86_64"]
        assert len(repos) > 0, "omnia_repo_url_rhel_x86_64 must not be empty"

    def test_omnia_repo_url_aarch64_is_list(self, repo_manager_config):
        """omnia_repo_url_rhel_aarch64 must be a list."""
        repos = repo_manager_config["omnia_repo_url_rhel_aarch64"]
        assert isinstance(repos, list), "omnia_repo_url_rhel_aarch64 must be a list"

    def test_omnia_repo_url_aarch64_not_empty(self, repo_manager_config):
        """omnia_repo_url_rhel_aarch64 must not be empty."""
        repos = repo_manager_config["omnia_repo_url_rhel_aarch64"]
        assert len(repos) > 0, "omnia_repo_url_rhel_aarch64 must not be empty"

    def test_omnia_repos_have_required_fields(self, repo_manager_config):
        """Each omnia_repo_url entry must have url, gpgkey, and name."""
        for key in ["omnia_repo_url_rhel_x86_64", "omnia_repo_url_rhel_aarch64"]:
            repos = repo_manager_config.get(key, [])
            for repo in repos:
                for field in ["url", "gpgkey", "name"]:
                    assert field in repo, (
                        f"{key} entry missing required field '{field}': {repo}"
                    )

    def test_omnia_repo_urls_are_http(self, repo_manager_config):
        """All omnia repo URLs must start with http:// or https://."""
        for key in ["omnia_repo_url_rhel_x86_64", "omnia_repo_url_rhel_aarch64"]:
            repos = repo_manager_config.get(key, [])
            for repo in repos:
                url = repo.get("url", "")
                assert url.startswith(("http://", "https://")), (
                    f"{key} repo '{repo.get('name')}' has invalid URL: {url}"
                )

    def test_no_duplicate_repo_names_x86_64(self, repo_manager_config):
        """omnia_repo_url_rhel_x86_64 must not have duplicate repo names."""
        repos = repo_manager_config.get("omnia_repo_url_rhel_x86_64", [])
        names = [r["name"] for r in repos if "name" in r]
        assert len(names) == len(set(names)), (
            f"Duplicate repo names in omnia_repo_url_rhel_x86_64: "
            f"{[n for n in names if names.count(n) > 1]}"
        )

    def test_no_duplicate_repo_names_aarch64(self, repo_manager_config):
        """omnia_repo_url_rhel_aarch64 must not have duplicate repo names."""
        repos = repo_manager_config.get("omnia_repo_url_rhel_aarch64", [])
        names = [r["name"] for r in repos if "name" in r]
        assert len(names) == len(set(names)), (
            f"Duplicate repo names in omnia_repo_url_rhel_aarch64: "
            f"{[n for n in names if names.count(n) > 1]}"
        )

    def test_repo_names_are_non_empty_strings(self, repo_manager_config):
        """All repo names must be non-empty strings."""
        for key in ["omnia_repo_url_rhel_x86_64", "omnia_repo_url_rhel_aarch64"]:
            repos = repo_manager_config.get(key, [])
            for repo in repos:
                name = repo.get("name")
                assert isinstance(name, str), (
                    f"{key} repo name must be a string, got {type(name)}"
                )
                assert len(name.strip()) > 0, (
                    f"{key} repo name must not be empty"
                )

    def test_optional_fields_are_null_or_absent(self, repo_manager_config):
        """Optional fields, if present, must be null or a list."""
        optional_keys = [
            "user_registry",
            "user_repo_url_x86_64",
            "user_repo_url_aarch64",
            "rhel_os_url_x86_64",
            "rhel_os_url_aarch64",
            "additional_repos_x86_64",
            "additional_repos_aarch64",
        ]
        for key in optional_keys:
            if key in repo_manager_config:
                val = repo_manager_config[key]
                assert val is None or isinstance(val, list), (
                    f"'{key}' must be null or a list, got {type(val)}"
                )


# ---------------------------------------------------------------------------
# JSON schema validation tests (positive and negative)
# ---------------------------------------------------------------------------
class TestRepoManagerConfigSchemaValidation:
    """Validate data against the actual JSON schema using jsonschema."""

    def test_default_config_validates(
        self, repo_manager_config, repo_manager_config_schema
    ):
        """The default repo_manager_config.yml must validate against the schema."""
        jsonschema.validate(
            instance=repo_manager_config, schema=repo_manager_config_schema
        )

    def test_minimal_valid_config(self, repo_manager_config_schema):
        """A minimal valid config (only required fields) must pass validation."""
        minimal = {
            "omnia_repo_url_rhel_x86_64": [
                {
                    "url": "https://example.com/repo/",
                    "gpgkey": "https://example.com/gpg",
                    "name": "test-repo",
                }
            ],
            "omnia_repo_url_rhel_aarch64": [
                {
                    "url": "https://example.com/repo-arm/",
                    "gpgkey": "https://example.com/gpg",
                    "name": "test-repo-arm",
                }
            ],
        }
        jsonschema.validate(instance=minimal, schema=repo_manager_config_schema)

    def test_required_fields_can_be_null(self, repo_manager_config_schema):
        """Required fields with null values must pass (type allows null)."""
        data = {
            "omnia_repo_url_rhel_x86_64": None,
            "omnia_repo_url_rhel_aarch64": None,
        }
        jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_config_with_all_optional_null(self, repo_manager_config_schema):
        """Config with all optional fields set to null must pass validation."""
        data = {
            "omnia_repo_url_rhel_x86_64": [
                {
                    "url": "https://example.com/repo/",
                    "gpgkey": "",
                    "name": "test-repo",
                }
            ],
            "omnia_repo_url_rhel_aarch64": None,
            "user_registry": None,
            "user_repo_url_x86_64": None,
            "user_repo_url_aarch64": None,
            "rhel_os_url_x86_64": None,
            "rhel_os_url_aarch64": None,
            "additional_repos_x86_64": None,
            "additional_repos_aarch64": None,
            "rhel_subscription_repo_config_x86_64": None,
            "rhel_subscription_repo_config_aarch64": None,
        }
        jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_config_with_user_registry(self, repo_manager_config_schema):
        """Config with user_registry entries must pass validation."""
        data = {
            "omnia_repo_url_rhel_x86_64": None,
            "omnia_repo_url_rhel_aarch64": None,
            "user_registry": [
                {"host": "172.16.107.254:4000"},
                {
                    "host": "10.0.0.1:5000",
                    "cert_path": "/path/to/domain.crt",
                    "key_path": "/path/to/domain.key",
                },
            ],
        }
        jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_config_with_user_repo_url(self, repo_manager_config_schema):
        """Config with user_repo_url entries must pass validation."""
        data = {
            "omnia_repo_url_rhel_x86_64": None,
            "omnia_repo_url_rhel_aarch64": None,
            "user_repo_url_x86_64": [
                {
                    "url": "https://my-repo.example.com/x86_64/",
                    "gpgkey": "",
                    "name": "slurm_custom",
                }
            ],
        }
        jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_config_with_additional_repos(self, repo_manager_config_schema):
        """Config with additional_repos entries must pass validation."""
        data = {
            "omnia_repo_url_rhel_x86_64": None,
            "omnia_repo_url_rhel_aarch64": None,
            "additional_repos_x86_64": [
                {
                    "url": "https://rpm.grafana.com/",
                    "gpgkey": "",
                    "name": "grafana",
                }
            ],
        }
        jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_config_with_rhel_os_url(self, repo_manager_config_schema):
        """Config with rhel_os_url entries must pass validation."""
        data = {
            "omnia_repo_url_rhel_x86_64": None,
            "omnia_repo_url_rhel_aarch64": None,
            "rhel_os_url_x86_64": [
                {
                    "url": "http://baseos.example.com/BaseOS/x86_64/os/",
                    "gpgkey": "http://baseos.example.com/RPM-GPG-KEY",
                    "name": "baseos",
                }
            ],
        }
        jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_config_with_subscription_repo_config(self, repo_manager_config_schema):
        """Config with rhel_subscription_repo_config must pass validation."""
        data = {
            "omnia_repo_url_rhel_x86_64": None,
            "omnia_repo_url_rhel_aarch64": None,
            "rhel_subscription_repo_config_x86_64": [
                {
                    "url": "https://cdn.redhat.com/content/dist/rhel10/10.0/x86_64/baseos/os/",
                    "name": "baseos",
                }
            ],
        }
        jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_repo_entry_with_ssl_fields(self, repo_manager_config_schema):
        """Repo entries with all SSL fields must pass validation."""
        data = {
            "omnia_repo_url_rhel_x86_64": [
                {
                    "url": "https://secure-repo.example.com/",
                    "gpgkey": "https://secure-repo.example.com/gpg",
                    "name": "secure-repo",
                    "sslcacert": "/path/to/ca.crt",
                    "sslclientkey": "/path/to/client.key",
                    "sslclientcert": "/path/to/client.crt",
                }
            ],
            "omnia_repo_url_rhel_aarch64": None,
        }
        jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_repo_entry_with_policy(self, repo_manager_config_schema):
        """Repo entries with policy field must pass validation."""
        data = {
            "omnia_repo_url_rhel_x86_64": [
                {
                    "url": "https://example.com/repo/",
                    "gpgkey": "",
                    "name": "test-repo",
                    "policy": "always",
                }
            ],
            "omnia_repo_url_rhel_aarch64": None,
        }
        jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_gpgkey_can_be_empty_string(self, repo_manager_config_schema):
        """gpgkey set to empty string must pass (disables gpgcheck)."""
        data = {
            "omnia_repo_url_rhel_x86_64": [
                {
                    "url": "https://example.com/repo/",
                    "gpgkey": "",
                    "name": "no-gpg-repo",
                }
            ],
            "omnia_repo_url_rhel_aarch64": None,
        }
        jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    # --- Negative tests ---

    def test_missing_both_required_fails(self, repo_manager_config_schema):
        """Missing both required fields must fail validation."""
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance={}, schema=repo_manager_config_schema)

    def test_missing_x86_64_required_fails(self, repo_manager_config_schema):
        """Missing omnia_repo_url_rhel_x86_64 must fail validation."""
        data = {
            "omnia_repo_url_rhel_aarch64": None,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_missing_aarch64_required_fails(self, repo_manager_config_schema):
        """Missing omnia_repo_url_rhel_aarch64 must fail validation."""
        data = {
            "omnia_repo_url_rhel_x86_64": None,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_additional_property_fails(self, repo_manager_config_schema):
        """Unknown top-level property must fail (additionalProperties: false)."""
        data = {
            "omnia_repo_url_rhel_x86_64": None,
            "omnia_repo_url_rhel_aarch64": None,
            "unknown_field": "value",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_omnia_repo_url_wrong_type_fails(self, repo_manager_config_schema):
        """omnia_repo_url as string must fail (must be array or null)."""
        data = {
            "omnia_repo_url_rhel_x86_64": "not_an_array",
            "omnia_repo_url_rhel_aarch64": None,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_repo_entry_missing_url_fails(self, repo_manager_config_schema):
        """Repo entry without url must fail validation."""
        data = {
            "omnia_repo_url_rhel_x86_64": [
                {"gpgkey": "", "name": "test"}
            ],
            "omnia_repo_url_rhel_aarch64": None,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_repo_entry_missing_name_fails(self, repo_manager_config_schema):
        """Repo entry without name must fail validation."""
        data = {
            "omnia_repo_url_rhel_x86_64": [
                {"url": "https://example.com/", "gpgkey": ""}
            ],
            "omnia_repo_url_rhel_aarch64": None,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_repo_entry_missing_gpgkey_fails(self, repo_manager_config_schema):
        """Repo entry without gpgkey must fail validation."""
        data = {
            "omnia_repo_url_rhel_x86_64": [
                {"url": "https://example.com/", "name": "test"}
            ],
            "omnia_repo_url_rhel_aarch64": None,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_repo_url_without_scheme_fails(self, repo_manager_config_schema):
        """Repo URL without http/https scheme must fail (pattern constraint)."""
        data = {
            "omnia_repo_url_rhel_x86_64": [
                {
                    "url": "ftp://example.com/repo/",
                    "gpgkey": "",
                    "name": "bad-url-repo",
                }
            ],
            "omnia_repo_url_rhel_aarch64": None,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_user_registry_missing_host_fails(self, repo_manager_config_schema):
        """user_registry entry without host must fail validation."""
        data = {
            "omnia_repo_url_rhel_x86_64": None,
            "omnia_repo_url_rhel_aarch64": None,
            "user_registry": [
                {"cert_path": "/path/to/cert.crt"}
            ],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_user_registry_invalid_host_pattern_fails(self, repo_manager_config_schema):
        """user_registry host without port must fail (pattern requires IP:port)."""
        data = {
            "omnia_repo_url_rhel_x86_64": None,
            "omnia_repo_url_rhel_aarch64": None,
            "user_registry": [
                {"host": "172.16.107.254"}
            ],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_subscription_repo_missing_url_fails(self, repo_manager_config_schema):
        """rhel_subscription_repo_config entry without url must fail."""
        data = {
            "omnia_repo_url_rhel_x86_64": None,
            "omnia_repo_url_rhel_aarch64": None,
            "rhel_subscription_repo_config_x86_64": [
                {"name": "baseos"}
            ],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_subscription_repo_missing_name_fails(self, repo_manager_config_schema):
        """rhel_subscription_repo_config entry without name must fail."""
        data = {
            "omnia_repo_url_rhel_x86_64": None,
            "omnia_repo_url_rhel_aarch64": None,
            "rhel_subscription_repo_config_x86_64": [
                {"url": "https://cdn.redhat.com/content/"}
            ],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_repo_name_empty_string_fails(self, repo_manager_config_schema):
        """Repo name that is empty string must fail (minLength: 1)."""
        data = {
            "omnia_repo_url_rhel_x86_64": [
                {
                    "url": "https://example.com/repo/",
                    "gpgkey": "",
                    "name": "",
                }
            ],
            "omnia_repo_url_rhel_aarch64": None,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_repo_url_empty_string_fails(self, repo_manager_config_schema):
        """Repo URL that is empty string must fail (minLength: 1)."""
        data = {
            "omnia_repo_url_rhel_x86_64": [
                {
                    "url": "",
                    "gpgkey": "",
                    "name": "empty-url-repo",
                }
            ],
            "omnia_repo_url_rhel_aarch64": None,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=repo_manager_config_schema)

    def test_invalid_policy_enum_fails(self, repo_manager_config_schema):
        """Invalid policy value must fail validation."""
        data = {
            "omnia_repo_url_rhel_x86_64": [
                {
                    "url": "https://example.com/repo/",
                    "gpgkey": "",
                    "name": "test-repo",
                    "policy": "sometimes",
                }
            ],
            "omnia_repo_url_rhel_aarch64": None,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=repo_manager_config_schema)
