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
"""Tests for package_groups.yml (functional group mapping) structure and content."""

import re


VALID_ARCH_SUFFIXES = ("_x86_64", "_aarch64")


class TestFunctionalGroupPackagesStructure:
    """Validate the structure of functional_group_packages.yml."""

    def test_base_packages_exists(self, functional_group_packages):
        """base_packages must be present and non-empty."""
        assert "base_packages" in functional_group_packages
        assert isinstance(functional_group_packages["base_packages"], list)
        assert len(functional_group_packages["base_packages"]) > 0

    def test_functional_groups_exists(self, functional_group_packages):
        """functional_groups must be present and non-empty."""
        assert "functional_groups" in functional_group_packages
        assert isinstance(functional_group_packages["functional_groups"], dict)
        assert len(functional_group_packages["functional_groups"]) > 0

    def test_each_group_has_packages_key(self, functional_group_packages):
        """Every functional group entry must have a 'packages' key."""
        for group_name, group_data in functional_group_packages["functional_groups"].items():
            assert "packages" in group_data, (
                f"Functional group '{group_name}' missing 'packages' key"
            )
            assert isinstance(group_data["packages"], list), (
                f"Functional group '{group_name}' packages must be a list"
            )

    def test_group_names_have_arch_suffix(self, functional_group_packages):
        """Every functional group name must end with _x86_64 or _aarch64."""
        for group_name in functional_group_packages["functional_groups"]:
            assert any(group_name.endswith(suffix) for suffix in VALID_ARCH_SUFFIXES), (
                f"Functional group '{group_name}' must end with "
                f"one of {VALID_ARCH_SUFFIXES}"
            )

    def test_base_packages_are_strings(self, functional_group_packages):
        """All base_packages entries must be non-empty strings."""
        for pkg in functional_group_packages["base_packages"]:
            assert isinstance(pkg, str), f"base_packages entry must be string, got {type(pkg)}"
            assert len(pkg.strip()) > 0, "base_packages entry must not be empty"

    def test_group_packages_are_strings(self, functional_group_packages):
        """All group package entries must be non-empty strings."""
        for group_name, group_data in functional_group_packages["functional_groups"].items():
            for pkg in group_data["packages"]:
                assert isinstance(pkg, str), (
                    f"Package in '{group_name}' must be string, got {type(pkg)}"
                )
                assert len(pkg.strip()) > 0, (
                    f"Package in '{group_name}' must not be empty"
                )

    def test_no_duplicate_base_packages(self, functional_group_packages):
        """base_packages must not have duplicates."""
        pkgs = functional_group_packages["base_packages"]
        assert len(pkgs) == len(set(pkgs)), (
            f"Duplicate base_packages found: "
            f"{[p for p in pkgs if pkgs.count(p) > 1]}"
        )

    def test_no_duplicate_group_packages(self, functional_group_packages):
        """No functional group should have duplicate packages."""
        for group_name, group_data in functional_group_packages["functional_groups"].items():
            pkgs = group_data["packages"]
            assert len(pkgs) == len(set(pkgs)), (
                f"Duplicate packages in '{group_name}': "
                f"{[p for p in pkgs if pkgs.count(p) > 1]}"
            )


class TestFunctionalGroupPackagesContent:
    """Validate expected content in functional_group_packages.yml."""

    def test_base_has_essential_packages(self, functional_group_packages):
        """Base packages must include essential OS packages."""
        base = functional_group_packages["base_packages"]
        essentials = ["systemd", "kernel", "dracut", "NetworkManager"]
        for pkg in essentials:
            assert pkg in base, f"Essential base package '{pkg}' missing"

    def test_os_x86_64_exists(self, functional_group_packages):
        """os_x86_64 functional group must exist."""
        assert "os_x86_64" in functional_group_packages["functional_groups"]

    def test_slurm_groups_have_munge(self, functional_group_packages):
        """All slurm_* groups must include munge."""
        for group_name, group_data in functional_group_packages["functional_groups"].items():
            if "slurm" in group_name and group_data["packages"]:
                assert "munge" in group_data["packages"], (
                    f"Slurm group '{group_name}' missing 'munge' package"
                )


class TestConfigConsistency:
    """Validate consistency between config files."""

    def test_functional_groups_have_arch_suffix_in_mapping(
        self, functional_group_packages
    ):
        """All functional groups in mapping must have valid arch suffix."""
        mapping_groups = functional_group_packages.get("functional_groups", {})
        for group_name in mapping_groups:
            assert any(
                group_name.endswith(suffix) for suffix in VALID_ARCH_SUFFIXES
            ), (
                f"Functional group '{group_name}' in functional_group_packages.yml "
                f"must end with one of {VALID_ARCH_SUFFIXES}"
            )
