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

"""Unit tests for adapter_policy module."""

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(__file__)
CATALOG_PARSER_DIR = os.path.dirname(HERE)
PROJECT_ROOT = os.path.dirname(CATALOG_PARSER_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.catalog.adapter_policy import (
    validate_policy_config,
    discover_architectures,
    discover_os_versions,
    transform_package,
    apply_substring_filter,
    compute_common_packages,
    apply_extract_common_filter,
    apply_extract_unique_filter,
    apply_filter,
    merge_transform,
    compute_common_keys_from_roles,
    derive_common_role,
    check_conditions,
    process_target_spec,
    write_config_file,
    generate_configs_from_policy,
    _DEFAULT_POLICY_PATH,
    _DEFAULT_SCHEMA_PATH,
)
from core.catalog import adapter_policy_schema_consts as schema


class TestValidatePolicyConfig(unittest.TestCase):
    """Tests for validate_policy_config function."""

    def setUp(self):
        self.valid_policy = {
            "version": "2.0.0",
            "targets": {
                "test.json": {
                    "sources": [
                        {
                            "source_file": "source.json",
                            "pulls": [{"source_key": "role1"}]
                        }
                    ]
                }
            }
        }
        self.schema_path = _DEFAULT_SCHEMA_PATH
        with open(self.schema_path, "r", encoding="utf-8") as f:
            self.schema_config = json.load(f)

    def test_valid_policy_passes_validation(self):
        """Valid policy should not raise any exception."""
        validate_policy_config(
            self.valid_policy,
            self.schema_config,
            policy_path="test_policy.json",
            schema_path=self.schema_path
        )

    def test_missing_version_raises_error(self):
        """Policy missing required 'version' field should raise ValueError."""
        invalid_policy = {"targets": {}}
        with self.assertRaises(ValueError) as ctx:
            validate_policy_config(
                invalid_policy,
                self.schema_config,
                policy_path="test_policy.json",
                schema_path=self.schema_path
            )
        self.assertIn("Adapter policy validation failed", str(ctx.exception))
        self.assertIn("version", str(ctx.exception))

    def test_missing_targets_raises_error(self):
        """Policy missing required 'targets' field should raise ValueError."""
        invalid_policy = {"version": "2.0.0"}
        with self.assertRaises(ValueError) as ctx:
            validate_policy_config(
                invalid_policy,
                self.schema_config,
                policy_path="test_policy.json",
                schema_path=self.schema_path
            )
        self.assertIn("Adapter policy validation failed", str(ctx.exception))
        self.assertIn("targets", str(ctx.exception))

    def test_invalid_target_spec_raises_error(self):
        """Target spec missing 'sources' should raise ValueError."""
        invalid_policy = {
            "version": "2.0.0",
            "targets": {
                "test.json": {}
            }
        }
        with self.assertRaises(ValueError) as ctx:
            validate_policy_config(
                invalid_policy,
                self.schema_config,
                policy_path="test_policy.json",
                schema_path=self.schema_path
            )
        self.assertIn("Adapter policy validation failed", str(ctx.exception))

    def test_allowlist_filter_policy_validates(self):
        """Policy using allowlist filter type should validate against schema."""
        policy = {
            "version": "2.0.0",
            "targets": {
                "openldap.json": {
                    "sources": [
                        {
                            "source_file": "base_os.json",
                            "pulls": [
                                {
                                    "source_key": "Base OS",
                                    "filter": {
                                        "type": "allowlist",
                                        "field": "package",
                                        "values": ["openldap-clients"],
                                        "case_sensitive": False,
                                    },
                                }
                            ],
                        }
                    ]
                }
            },
        }

        validate_policy_config(
            policy,
            self.schema_config,
            policy_path="test_policy.json",
            schema_path=self.schema_path,
        )

    def test_field_in_filter_policy_validates(self):
        """Policy using field_in filter type should validate against schema."""
        policy = {
            "version": "2.0.0",
            "targets": {
                "openldap.json": {
                    "sources": [
                        {
                            "source_file": "base_os.json",
                            "pulls": [
                                {
                                    "source_key": "Base OS",
                                    "filter": {
                                        "type": "field_in",
                                        "field": "feature",
                                        "values": ["openldap"],
                                        "case_sensitive": False,
                                    },
                                }
                            ],
                        }
                    ]
                }
            },
        }

        validate_policy_config(
            policy,
            self.schema_config,
            policy_path="test_policy.json",
            schema_path=self.schema_path,
        )

    def test_any_of_filter_requires_filters(self):
        """any_of filter must define nested filters."""
        policy = {
            "version": "2.0.0",
            "targets": {
                "openldap.json": {
                    "sources": [
                        {
                            "source_file": "base_os.json",
                            "pulls": [
                                {"source_key": "Base OS", "filter": {"type": "any_of"}}
                            ],
                        }
                    ]
                }
            },
        }

        with self.assertRaises(ValueError) as ctx:
            validate_policy_config(
                policy,
                self.schema_config,
                policy_path="test_policy.json",
                schema_path=self.schema_path,
            )
        self.assertIn("Adapter policy validation failed", str(ctx.exception))

    def test_any_of_filter_policy_validates(self):
        """Policy using any_of filter type should validate against schema."""
        policy = {
            "version": "2.0.0",
            "targets": {
                "openldap.json": {
                    "sources": [
                        {
                            "source_file": "base_os.json",
                            "pulls": [
                                {
                                    "source_key": "Base OS",
                                    "filter": {
                                        "type": "any_of",
                                        "filters": [
                                            {"type": "substring", "values": ["ldap"]},
                                            {"type": "field_in", "field": "feature", "values": ["openldap"]},
                                        ],
                                    },
                                }
                            ],
                        }
                    ]
                }
            },
        }

        validate_policy_config(
            policy,
            self.schema_config,
            policy_path="test_policy.json",
            schema_path=self.schema_path,
        )


class TestDiscoverArchitectures(unittest.TestCase):
    """Tests for discover_architectures function."""

    def test_discovers_architecture_directories(self):
        """Should return list of subdirectory names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "x86_64"))
            os.makedirs(os.path.join(tmpdir, "aarch64"))
            # Create a file (should be ignored)
            with open(os.path.join(tmpdir, "readme.txt"), "w") as f:
                f.write("test")

            archs = discover_architectures(tmpdir)
            self.assertEqual(sorted(archs), ["aarch64", "x86_64"])

    def test_returns_empty_for_nonexistent_dir(self):
        """Should return empty list for non-existent directory."""
        archs = discover_architectures("/nonexistent/path")
        self.assertEqual(archs, [])

    def test_returns_empty_for_empty_dir(self):
        """Should return empty list for empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archs = discover_architectures(tmpdir)
            self.assertEqual(archs, [])


class TestDiscoverOsVersions(unittest.TestCase):
    """Tests for discover_os_versions function."""

    def test_discovers_os_and_versions(self):
        """Should return list of (os_family, version) tuples."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "x86_64", "rhel", "9.0"))
            os.makedirs(os.path.join(tmpdir, "x86_64", "rhel", "8.0"))
            os.makedirs(os.path.join(tmpdir, "x86_64", "ubuntu", "22.04"))

            results = discover_os_versions(tmpdir, "x86_64")
            self.assertEqual(len(results), 3)
            self.assertIn(("rhel", "9.0"), results)
            self.assertIn(("rhel", "8.0"), results)
            self.assertIn(("ubuntu", "22.04"), results)

    def test_returns_empty_for_nonexistent_arch(self):
        """Should return empty list for non-existent architecture."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = discover_os_versions(tmpdir, "nonexistent")
            self.assertEqual(results, [])


class TestTransformPackage(unittest.TestCase):
    """Tests for transform_package function."""

    def test_no_transform_returns_copy(self):
        """No transform config should return a copy of the package."""
        pkg = {"name": "test", "version": "1.0"}
        result = transform_package(pkg, None)
        self.assertEqual(result, pkg)
        self.assertIsNot(result, pkg)

    def test_exclude_fields(self):
        """Should exclude specified fields."""
        pkg = {"name": "test", "version": "1.0", "architecture": "x86_64"}
        transform = {schema.EXCLUDE_FIELDS: ["architecture"]}
        result = transform_package(pkg, transform)
        self.assertEqual(result, {"name": "test", "version": "1.0"})

    def test_rename_fields(self):
        """Should rename specified fields."""
        pkg = {"name": "test", "ver": "1.0"}
        transform = {schema.RENAME_FIELDS: {"ver": "version"}}
        result = transform_package(pkg, transform)
        self.assertEqual(result, {"name": "test", "version": "1.0"})

    def test_exclude_and_rename_combined(self):
        """Should apply both exclude and rename."""
        pkg = {"name": "test", "ver": "1.0", "arch": "x86_64"}
        transform = {
            schema.EXCLUDE_FIELDS: ["arch"],
            schema.RENAME_FIELDS: {"ver": "version"}
        }
        result = transform_package(pkg, transform)
        self.assertEqual(result, {"name": "test", "version": "1.0"})


class TestApplySubstringFilter(unittest.TestCase):
    """Tests for apply_substring_filter function."""

    def test_filters_by_substring(self):
        """Should filter packages by substring match."""
        packages = [
            {"package": "kubernetes-client"},
            {"package": "kubernetes-server"},
            {"package": "docker-ce"},
        ]
        filter_config = {
            schema.FIELD: "package",
            schema.VALUES: ["kubernetes"]
        }
        result = apply_substring_filter(packages, filter_config)
        self.assertEqual(len(result), 2)
        self.assertTrue(all("kubernetes" in p["package"] for p in result))

    def test_case_insensitive_by_default(self):
        """Should be case-insensitive by default."""
        packages = [
            {"package": "Kubernetes-Client"},
            {"package": "docker-ce"},
        ]
        filter_config = {
            schema.FIELD: "package",
            schema.VALUES: ["kubernetes"]
        }
        result = apply_substring_filter(packages, filter_config)
        self.assertEqual(len(result), 1)

    def test_case_sensitive_when_specified(self):
        """Should be case-sensitive when specified."""
        packages = [
            {"package": "Kubernetes-Client"},
            {"package": "kubernetes-server"},
        ]
        filter_config = {
            schema.FIELD: "package",
            schema.VALUES: ["kubernetes"],
            schema.CASE_SENSITIVE: True
        }
        result = apply_substring_filter(packages, filter_config)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["package"], "kubernetes-server")

    def test_empty_values_returns_all(self):
        """Empty values list should return all packages."""
        packages = [{"package": "test1"}, {"package": "test2"}]
        filter_config = {schema.FIELD: "package", schema.VALUES: []}
        result = apply_substring_filter(packages, filter_config)
        self.assertEqual(result, packages)


class TestAllowlistAndFieldFilters(unittest.TestCase):
    def test_allowlist_matches_exact_package_names(self):
        packages = [
            {"package": "openldap-clients"},
            {"package": "openldap-servers"},
            {"package": "openmpi"},
        ]
        filter_config = {
            schema.TYPE: schema.ALLOWLIST_FILTER,
            schema.FIELD: "package",
            schema.VALUES: ["openldap-clients"],
            schema.CASE_SENSITIVE: False,
        }

        result = apply_filter(packages, {}, "Base OS", filter_config)
        self.assertEqual([p["package"] for p in result], ["openldap-clients"])

    def test_field_in_matches_classification_field(self):
        packages = [
            {"package": "vendor-ldap", "feature": "openldap"},
            {"package": "vendor-ldap2", "feature": "other"},
            {"package": "no-feature"},
        ]
        filter_config = {
            schema.TYPE: schema.FIELD_IN_FILTER,
            schema.FIELD: "feature",
            schema.VALUES: ["openldap"],
            schema.CASE_SENSITIVE: False,
        }

        result = apply_filter(packages, {}, "Base OS", filter_config)
        self.assertEqual([p["package"] for p in result], ["vendor-ldap"])

    def test_any_of_combines_multiple_strategies(self):
        packages = [
            {"package": "openldap-clients"},
            {"package": "vendor-ldap", "feature": "openldap"},
            {"package": "slapd-utils"},
            {"package": "unrelated"},
        ]

        filter_config = {
            schema.TYPE: schema.ANY_OF_FILTER,
            schema.FILTERS: [
                {
                    schema.TYPE: schema.ALLOWLIST_FILTER,
                    schema.FIELD: "package",
                    schema.VALUES: ["openldap-clients"],
                    schema.CASE_SENSITIVE: False,
                },
                {
                    schema.TYPE: schema.FIELD_IN_FILTER,
                    schema.FIELD: "feature",
                    schema.VALUES: ["openldap"],
                    schema.CASE_SENSITIVE: False,
                },
                {
                    schema.TYPE: schema.SUBSTRING_FILTER,
                    schema.FIELD: "package",
                    schema.VALUES: ["slapd"],
                    schema.CASE_SENSITIVE: False,
                },
            ],
        }

        result = apply_filter(packages, {}, "Base OS", filter_config)
        self.assertEqual(
            [p["package"] for p in result],
            ["openldap-clients", "vendor-ldap", "slapd-utils"],
        )


class TestComputeCommonPackages(unittest.TestCase):
    """Tests for compute_common_packages function."""

    def test_finds_common_packages(self):
        """Should find packages common across multiple keys."""
        source_data = {
            "role1": {schema.PACKAGES: [
                {"name": "common-pkg", "version": "1.0"},
                {"name": "unique1", "version": "1.0"},
            ]},
            "role2": {schema.PACKAGES: [
                {"name": "common-pkg", "version": "1.0"},
                {"name": "unique2", "version": "1.0"},
            ]},
        }
        common_keys, key_to_pkg = compute_common_packages(
            source_data, ["role1", "role2"], min_occurrences=2
        )
        self.assertEqual(len(common_keys), 1)

    def test_respects_min_occurrences(self):
        """Should respect min_occurrences threshold."""
        source_data = {
            "role1": {schema.PACKAGES: [{"name": "pkg1"}]},
            "role2": {schema.PACKAGES: [{"name": "pkg1"}]},
            "role3": {schema.PACKAGES: [{"name": "pkg2"}]},
        }
        common_keys, _ = compute_common_packages(
            source_data, ["role1", "role2", "role3"], min_occurrences=3
        )
        self.assertEqual(len(common_keys), 0)


class TestMergeTransform(unittest.TestCase):
    """Tests for merge_transform function."""

    def test_none_inputs_return_none(self):
        """Both None should return None."""
        self.assertIsNone(merge_transform(None, None))

    def test_base_only(self):
        """Only base should return base."""
        base = {schema.EXCLUDE_FIELDS: ["arch"]}
        self.assertEqual(merge_transform(base, None), base)

    def test_override_only(self):
        """Only override should return override."""
        override = {schema.EXCLUDE_FIELDS: ["arch"]}
        self.assertEqual(merge_transform(None, override), override)

    def test_override_wins(self):
        """Override values should win."""
        base = {schema.EXCLUDE_FIELDS: ["arch"]}
        override = {schema.EXCLUDE_FIELDS: ["version"]}
        result = merge_transform(base, override)
        self.assertEqual(result[schema.EXCLUDE_FIELDS], ["version"])


class TestCheckConditions(unittest.TestCase):
    """Tests for check_conditions function."""

    def test_no_conditions_returns_true(self):
        """No conditions should always return True."""
        self.assertTrue(check_conditions(None, "x86_64", "rhel", "9.0"))

    def test_architecture_condition(self):
        """Should check architecture condition."""
        conditions = {schema.ARCHITECTURES: ["x86_64"]}
        self.assertTrue(check_conditions(conditions, "x86_64", "rhel", "9.0"))
        self.assertFalse(check_conditions(conditions, "aarch64", "rhel", "9.0"))

    def test_os_family_condition(self):
        """Should check OS family condition."""
        conditions = {schema.OS_FAMILIES: ["rhel"]}
        self.assertTrue(check_conditions(conditions, "x86_64", "rhel", "9.0"))
        self.assertFalse(check_conditions(conditions, "x86_64", "ubuntu", "22.04"))

    def test_os_version_condition(self):
        """Should check OS version condition."""
        conditions = {schema.OS_VERSIONS: ["9.0"]}
        self.assertTrue(check_conditions(conditions, "x86_64", "rhel", "9.0"))
        self.assertFalse(check_conditions(conditions, "x86_64", "rhel", "8.0"))

    def test_multiple_conditions_all_must_pass(self):
        """All conditions must pass."""
        conditions = {
            schema.ARCHITECTURES: ["x86_64"],
            schema.OS_FAMILIES: ["rhel"],
            schema.OS_VERSIONS: ["9.0"]
        }
        self.assertTrue(check_conditions(conditions, "x86_64", "rhel", "9.0"))
        self.assertFalse(check_conditions(conditions, "aarch64", "rhel", "9.0"))


class TestDeriveCommonRole(unittest.TestCase):
    """Tests for derive_common_role function."""

    def test_derives_common_packages(self):
        """Should derive common packages into new role."""
        target_roles = {
            "role1": [{"name": "common"}, {"name": "unique1"}],
            "role2": [{"name": "common"}, {"name": "unique2"}],
        }
        derive_common_role(
            target_roles,
            derived_key="common_role",
            from_keys=["role1", "role2"],
            min_occurrences=2,
            remove_from_sources=True
        )
        self.assertIn("common_role", target_roles)
        self.assertEqual(len(target_roles["common_role"]), 1)
        self.assertEqual(target_roles["common_role"][0]["name"], "common")

    def test_removes_from_sources_when_specified(self):
        """Should remove common packages from source roles."""
        target_roles = {
            "role1": [{"name": "common"}, {"name": "unique1"}],
            "role2": [{"name": "common"}, {"name": "unique2"}],
        }
        derive_common_role(
            target_roles,
            derived_key="common_role",
            from_keys=["role1", "role2"],
            min_occurrences=2,
            remove_from_sources=True
        )
        self.assertEqual(len(target_roles["role1"]), 1)
        self.assertEqual(target_roles["role1"][0]["name"], "unique1")

    def test_keeps_sources_when_not_removing(self):
        """Should keep source packages when remove_from_sources=False."""
        target_roles = {
            "role1": [{"name": "common"}, {"name": "unique1"}],
            "role2": [{"name": "common"}, {"name": "unique2"}],
        }
        derive_common_role(
            target_roles,
            derived_key="common_role",
            from_keys=["role1", "role2"],
            min_occurrences=2,
            remove_from_sources=False
        )
        self.assertEqual(len(target_roles["role1"]), 2)


class TestWriteConfigFile(unittest.TestCase):
    """Tests for write_config_file function."""

    def test_writes_valid_json(self):
        """Should write valid JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "subdir", "test.json")
            config = {
                "role1": {schema.CLUSTER: [{"name": "pkg1"}]},
                "role2": {schema.CLUSTER: [{"name": "pkg2"}]},
            }
            write_config_file(file_path, config)

            self.assertTrue(os.path.exists(file_path))
            with open(file_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertEqual(loaded["role1"][schema.CLUSTER][0]["name"], "pkg1")

    def test_creates_parent_directories(self):
        """Should create parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "a", "b", "c", "test.json")
            config = {"role1": {schema.CLUSTER: []}}
            write_config_file(file_path, config)
            self.assertTrue(os.path.exists(file_path))


class TestGenerateConfigsFromPolicy(unittest.TestCase):
    """Tests for generate_configs_from_policy function."""

    def setUp(self):
        self.test_fixtures_dir = os.path.join(CATALOG_PARSER_DIR, "test_fixtures")
        self.test_policy_path = os.path.join(self.test_fixtures_dir, "adapter_policy_test.json")

    def test_generates_output_files(self):
        """Should generate output JSON files from valid policy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create input directory structure
            input_dir = os.path.join(tmpdir, "input")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(os.path.join(input_dir, "x86_64", "rhel", "9.0"))

            # Create source file
            source_data = {
                "Base OS": {
                    schema.PACKAGES: [
                        {"package": "test-pkg", "version": "1.0"}
                    ]
                }
            }
            with open(os.path.join(input_dir, "x86_64", "rhel", "9.0", "base_os.json"), "w") as f:
                json.dump(source_data, f)

            # Create minimal policy
            policy = {
                "version": "2.0.0",
                "targets": {
                    "output.json": {
                        "sources": [{
                            "source_file": "base_os.json",
                            "pulls": [{"source_key": "Base OS", "target_key": "base_role"}]
                        }]
                    }
                }
            }
            policy_path = os.path.join(tmpdir, "policy.json")
            with open(policy_path, "w") as f:
                json.dump(policy, f)

            generate_configs_from_policy(
                input_dir=input_dir,
                output_dir=output_dir,
                policy_path=policy_path,
                schema_path=_DEFAULT_SCHEMA_PATH
            )

            output_file = os.path.join(output_dir, "x86_64", "rhel", "9.0", "output.json")
            self.assertTrue(os.path.exists(output_file))

    def test_generates_openldap_with_any_of_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = os.path.join(tmpdir, "input")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(os.path.join(input_dir, "x86_64", "rhel", "9.0"))

            source_data = {
                "Base OS": {
                    schema.PACKAGES: [
                        {"package": "openldap-clients", "type": "rpm", "architecture": ["x86_64"]},
                        {"package": "vendor-directory-client", "type": "rpm", "architecture": ["x86_64"], "feature": "openldap"},
                        {"package": "slapd-utils", "type": "rpm", "architecture": ["x86_64"]},
                        {"package": "bash", "type": "rpm", "architecture": ["x86_64"]},
                    ]
                }
            }
            with open(os.path.join(input_dir, "x86_64", "rhel", "9.0", "base_os.json"), "w") as f:
                json.dump(source_data, f)

            policy = {
                "version": "2.0.0",
                "targets": {
                    "openldap.json": {
                        "transform": {"exclude_fields": ["architecture"]},
                        "sources": [
                            {
                                "source_file": "base_os.json",
                                "pulls": [
                                    {
                                        "source_key": "Base OS",
                                        "target_key": "openldap",
                                        "filter": {
                                            "type": "any_of",
                                            "filters": [
                                                {"type": "allowlist", "field": "package", "values": ["openldap-clients"], "case_sensitive": False},
                                                {"type": "field_in", "field": "feature", "values": ["openldap"], "case_sensitive": False},
                                                {"type": "substring", "field": "package", "values": ["slapd"], "case_sensitive": False},
                                            ],
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                },
            }
            policy_path = os.path.join(tmpdir, "policy.json")
            with open(policy_path, "w") as f:
                json.dump(policy, f)

            generate_configs_from_policy(
                input_dir=input_dir,
                output_dir=output_dir,
                policy_path=policy_path,
                schema_path=_DEFAULT_SCHEMA_PATH,
            )

            output_file = os.path.join(output_dir, "x86_64", "rhel", "9.0", "openldap.json")
            self.assertTrue(os.path.exists(output_file))

            with open(output_file, "r", encoding="utf-8") as f:
                out_json = json.load(f)

            self.assertIn("openldap", out_json)
            pkgs = out_json["openldap"][schema.CLUSTER]

            self.assertEqual(
                [p.get("package") for p in pkgs],
                ["openldap-clients", "vendor-directory-client", "slapd-utils"],
            )
            self.assertTrue(all("architecture" not in p for p in pkgs))

    def test_invalid_policy_raises_error(self):
        """Should raise ValueError for invalid policy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = os.path.join(tmpdir, "input")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(input_dir)

            # Create invalid policy (missing version)
            invalid_policy = {"targets": {}}
            policy_path = os.path.join(tmpdir, "invalid_policy.json")
            with open(policy_path, "w") as f:
                json.dump(invalid_policy, f)

            with self.assertRaises(ValueError) as ctx:
                generate_configs_from_policy(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    policy_path=policy_path,
                    schema_path=_DEFAULT_SCHEMA_PATH
                )
            self.assertIn("Adapter policy validation failed", str(ctx.exception))

    def test_missing_input_dir_raises_file_not_found(self):
        """Should raise FileNotFoundError if input_dir does not exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "output")
            missing_input_dir = os.path.join(tmpdir, "does_not_exist")

            with self.assertRaises(FileNotFoundError):
                generate_configs_from_policy(
                    input_dir=missing_input_dir,
                    output_dir=output_dir,
                    policy_path=_DEFAULT_POLICY_PATH,
                    schema_path=_DEFAULT_SCHEMA_PATH,
                )

    def test_missing_policy_file_raises_file_not_found(self):
        """Should raise FileNotFoundError if policy_path does not exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = os.path.join(tmpdir, "input")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(input_dir)

            missing_policy_path = os.path.join(tmpdir, "missing_policy.json")

            with self.assertRaises(FileNotFoundError):
                generate_configs_from_policy(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    policy_path=missing_policy_path,
                    schema_path=_DEFAULT_SCHEMA_PATH,
                )

    def test_missing_schema_file_raises_file_not_found(self):
        """Should raise FileNotFoundError if schema_path does not exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = os.path.join(tmpdir, "input")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(input_dir)

            missing_schema_path = os.path.join(tmpdir, "missing_schema.json")

            with self.assertRaises(FileNotFoundError):
                generate_configs_from_policy(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    policy_path=_DEFAULT_POLICY_PATH,
                    schema_path=missing_schema_path,
                )


class TestDefaultPaths(unittest.TestCase):
    """Tests for default path constants."""

    def test_default_policy_path_exists(self):
        """Default policy path should point to existing file."""
        self.assertTrue(
            os.path.exists(_DEFAULT_POLICY_PATH),
            f"Default policy file not found: {_DEFAULT_POLICY_PATH}"
        )

    def test_default_schema_path_exists(self):
        """Default schema path should point to existing file."""
        self.assertTrue(
            os.path.exists(_DEFAULT_SCHEMA_PATH),
            f"Default schema file not found: {_DEFAULT_SCHEMA_PATH}"
        )

    def test_default_policy_validates_against_schema(self):
        """Default policy should validate against default schema."""
        with open(_DEFAULT_POLICY_PATH, "r", encoding="utf-8") as f:
            policy = json.load(f)
        with open(_DEFAULT_SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_config = json.load(f)

        # Should not raise
        validate_policy_config(
            policy,
            schema_config,
            policy_path=_DEFAULT_POLICY_PATH,
            schema_path=_DEFAULT_SCHEMA_PATH
        )


class TestProcessTargetSpec(unittest.TestCase):
    """Tests for process_target_spec function."""

    def test_processes_simple_target(self):
        """Should process a simple target specification."""
        source_files = {
            "source.json": {
                "role1": {schema.PACKAGES: [{"name": "pkg1"}]}
            }
        }
        target_spec = {
            "sources": [{
                "source_file": "source.json",
                "pulls": [{"source_key": "role1", "target_key": "output_role"}]
            }]
        }
        target_configs = {}

        process_target_spec(
            target_file="output.json",
            target_spec=target_spec,
            source_files=source_files,
            target_configs=target_configs,
            arch="x86_64",
            os_family="rhel",
            os_version="9.0"
        )

        self.assertIn("output.json", target_configs)
        self.assertIn("output_role", target_configs["output.json"])

    def test_skips_when_conditions_not_met(self):
        """Should skip target when conditions are not met."""
        source_files = {"source.json": {"role1": {schema.PACKAGES: []}}}
        target_spec = {
            "conditions": {schema.ARCHITECTURES: ["aarch64"]},
            "sources": [{
                "source_file": "source.json",
                "pulls": [{"source_key": "role1"}]
            }]
        }
        target_configs = {}

        process_target_spec(
            target_file="output.json",
            target_spec=target_spec,
            source_files=source_files,
            target_configs=target_configs,
            arch="x86_64",
            os_family="rhel",
            os_version="9.0"
        )

        self.assertNotIn("output.json", target_configs)

    def test_applies_transform(self):
        """Should apply transform to packages."""
        source_files = {
            "source.json": {
                "role1": {schema.PACKAGES: [
                    {"name": "pkg1", "architecture": "x86_64"}
                ]}
            }
        }
        target_spec = {
            "transform": {schema.EXCLUDE_FIELDS: ["architecture"]},
            "sources": [{
                "source_file": "source.json",
                "pulls": [{"source_key": "role1", "target_key": "output_role"}]
            }]
        }
        target_configs = {}

        process_target_spec(
            target_file="output.json",
            target_spec=target_spec,
            source_files=source_files,
            target_configs=target_configs,
            arch="x86_64",
            os_family="rhel",
            os_version="9.0"
        )

        pkgs = target_configs["output.json"]["output_role"][schema.CLUSTER]
        self.assertNotIn("architecture", pkgs[0])


if __name__ == "__main__":
    unittest.main()
