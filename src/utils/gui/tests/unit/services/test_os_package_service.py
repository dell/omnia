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

"""Unit tests for OSPackageService."""

import json
import os
import pytest

from backend.services.os_package_service import OSPackageService


@pytest.fixture
def config_dir(tmp_path):
    """Create a minimal config directory structure for testing."""
    # Create rhel config dir with a sample bundle JSON
    rhel_dir = tmp_path / "x86_64" / "rhel" / "10.0"
    rhel_dir.mkdir(parents=True)

    # Create a sample bundle JSON file matching _iter_packages expectations
    bundle_data = {
        "default_packages": {
            "cluster": [
                {"package": "pkg1", "type": "rpm", "repo_name": "baseos"},
                {"package": "pkg2", "type": "rpm", "repo_name": "baseos"},
            ]
        }
    }
    (rhel_dir / "default_packages.json").write_text(json.dumps(bundle_data))
    (rhel_dir / "service_k8s.json").write_text(json.dumps({
        "service_k8s": {"cluster": [{"package": "k8s-pkg", "type": "rpm"}]}
    }))

    return tmp_path


@pytest.fixture
def service(config_dir):
    """Create an OSPackageService with test config directory."""
    return OSPackageService(config_dir=str(config_dir))


class TestListAvailableCombinations:
    """Tests for list_available_combinations."""

    def test_enumerates_directories(self, service):
        combos = service.list_available_combinations()
        assert len(combos) >= 1
        combo = combos[0]
        assert combo["os_family"] == "rhel"
        assert combo["arch"] == "x86_64"

    def test_preserves_directory_os_family(self, service, config_dir):
        # list_available_combinations returns the dir name as-is
        combos = service.list_available_combinations()
        os_families = [c["os_family"] for c in combos]
        assert "rhel" in os_families


class TestListAvailableBundles:
    """Tests for list_available_bundles."""

    def test_returns_bundles_for_valid_path(self, service):
        bundles = service.list_available_bundles("x86_64", "rhel", "10.0")
        assert len(bundles) >= 1
        names = [b["name"] for b in bundles]
        assert "default_packages" in names

    def test_returns_empty_for_nonexistent_path(self, service):
        bundles = service.list_available_bundles("x86_64", "ubuntu", "22.04")
        assert bundles == []

    def test_lowercases_os_family(self, service):
        bundles = service.list_available_bundles("x86_64", "RHEL", "10.0")
        assert len(bundles) >= 1

    def test_classifies_bundle_types(self, service):
        bundles = service.list_available_bundles("x86_64", "rhel", "10.0")
        types = {b["name"]: b["type"] for b in bundles}
        assert types["default_packages"] == "os"
        assert types["service_k8s"] == "functional"


class TestGetBundlePackages:
    """Tests for get_bundle_packages."""

    def test_returns_data_for_valid_bundle(self, service):
        result = service.get_bundle_packages("x86_64", "rhel", "10.0", "default_packages")
        # get_bundle_packages returns section-keyed dict; assert not empty
        assert isinstance(result, dict)
        assert "default_packages" in result
        assert len(result["default_packages"]) == 2
        assert result["default_packages"][0]["package"] == "pkg1"

    def test_returns_empty_for_nonexistent_bundle(self, service):
        result = service.get_bundle_packages("x86_64", "rhel", "10.0", "nonexistent_bundle")
        assert result == {}


class TestSearchPackages:
    """Tests for search_packages."""

    def test_returns_empty_for_nonexistent_path(self, service):
        result = service.search_packages("x86_64", "ubuntu", "22.04", "pkg")
        assert result == []


class TestValidatePathComponent:
    """Tests for path traversal prevention."""

    def test_rejects_path_traversal(self, service):
        with pytest.raises(ValueError):
            service.list_available_bundles("../etc", "rhel", "10.0")

    def test_rejects_slash(self, service):
        with pytest.raises(ValueError):
            service.list_available_bundles("x86_64", "rhel/../etc", "10.0")
