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

"""Unit tests for catalog validators (ER-BSM-002).

Tests base OS version pinning validation, schema version compatibility,
and catalog integrity checks.

Test coverage:
- TC-UT-006: Base OS version pinning validation (FR-1.1, AC-001, AC-002)
"""

import pytest

from core.catalog.models import Catalog
from core.catalog.validators import (
    BaseOSVersionNotPinnedError,
    extract_base_os_versions,
    validate_base_os_version_pinning,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_catalog_with_pinned_os():
    """Catalog with properly pinned BaseOS entries."""
    return Catalog(
        identifier="omnia-slurm-rhel-10-0-x86-64-aarch64",
        version="1.0",
        schema_version=2,
        name="Omnia Slurm Stack",
        base_os=[
            {"Name": "rhel", "Version": "10.0"},
            {"Name": "kernel", "Version": "5.14.0"},
        ],
        functional_layer=[],
        infrastructure=[],
        drivers_layer=[],
        drivers=[],
        functional_packages=[],
        os_packages=[],
        infrastructure_packages=[],
        miscellaneous=[],
    )


@pytest.fixture
def catalog_with_missing_version():
    """Catalog with BaseOS entry missing Version field."""
    return Catalog(
        identifier="test-catalog",
        version="1.0",
        schema_version=2,
        name="Test Catalog",
        base_os=[
            {"Name": "rhel"},  # Missing Version
            {"Name": "kernel", "Version": "5.14.0"},
        ],
        functional_layer=[],
        infrastructure=[],
        drivers_layer=[],
        drivers=[],
        functional_packages=[],
        os_packages=[],
        infrastructure_packages=[],
        miscellaneous=[],
    )


@pytest.fixture
def catalog_with_missing_name():
    """Catalog with BaseOS entry missing Name field."""
    return Catalog(
        identifier="test-catalog",
        version="1.0",
        schema_version=2,
        name="Test Catalog",
        base_os=[
            {"Version": "10.0"},  # Missing Name
            {"Name": "kernel", "Version": "5.14.0"},
        ],
        functional_layer=[],
        infrastructure=[],
        drivers_layer=[],
        drivers=[],
        functional_packages=[],
        os_packages=[],
        infrastructure_packages=[],
        miscellaneous=[],
    )


@pytest.fixture
def catalog_with_empty_base_os():
    """Catalog with empty BaseOS array."""
    return Catalog(
        identifier="test-catalog",
        version="1.0",
        schema_version=2,
        name="Test Catalog",
        base_os=[],
        functional_layer=[],
        infrastructure=[],
        drivers_layer=[],
        drivers=[],
        functional_packages=[],
        os_packages=[],
        infrastructure_packages=[],
        miscellaneous=[],
    )


# ---------------------------------------------------------------------------
# TC-UT-006: Base OS Version Pinning Validation
# ---------------------------------------------------------------------------

class TestBaseOSVersionPinning:
    """Test cases for base OS version pinning validation (FR-1.1, AC-001)."""

    def test_validate_base_os_version_pinning_success(
        self, valid_catalog_with_pinned_os
    ):
        """Valid catalog with all BaseOS entries pinned passes validation.
        
        Scenario: Successful base OS version pinning validation
          Given a catalog with all BaseOS entries having Name and Version
          When validate_base_os_version_pinning is called
          Then validation passes without raising an exception
          And an empty warnings list is returned
        """
        # Act
        warnings = validate_base_os_version_pinning(valid_catalog_with_pinned_os)

        # Assert
        assert warnings == [], "No warnings should be returned for valid catalog"

    def test_validate_base_os_version_pinning_missing_version(
        self, catalog_with_missing_version
    ):
        """Catalog with missing Version field raises BaseOSVersionNotPinnedError.
        
        Scenario: BaseOS entry missing Version field
          Given a catalog with a BaseOS entry missing the Version field
          When validate_base_os_version_pinning is called
          Then a BaseOSVersionNotPinnedError is raised
          And the error message includes the entry name "rhel"
        """
        # Act & Assert
        with pytest.raises(BaseOSVersionNotPinnedError) as exc_info:
            validate_base_os_version_pinning(catalog_with_missing_version)

        # Verify error details
        assert "rhel" in exc_info.value.unpinned_entries
        assert "missing explicit version" in str(exc_info.value)

    def test_validate_base_os_version_pinning_missing_name(
        self, catalog_with_missing_name
    ):
        """Catalog with missing Name field raises BaseOSVersionNotPinnedError.
        
        Scenario: BaseOS entry missing Name field
          Given a catalog with a BaseOS entry missing the Name field
          When validate_base_os_version_pinning is called
          Then a BaseOSVersionNotPinnedError is raised
          And the error message includes "BaseOS[0] (unnamed)"
        """
        # Act & Assert
        with pytest.raises(BaseOSVersionNotPinnedError) as exc_info:
            validate_base_os_version_pinning(catalog_with_missing_name)

        # Verify error details
        assert "BaseOS[0] (unnamed)" in exc_info.value.unpinned_entries

    def test_validate_base_os_version_pinning_empty_list(
        self, catalog_with_empty_base_os
    ):
        """Catalog with empty BaseOS array passes validation.
        
        Scenario: Empty BaseOS array
          Given a catalog with an empty BaseOS array
          When validate_base_os_version_pinning is called
          Then validation passes without raising an exception
        """
        # Act
        warnings = validate_base_os_version_pinning(catalog_with_empty_base_os)

        # Assert
        assert warnings == []

    def test_validate_base_os_version_pinning_multiple_unpinned(self):
        """Multiple unpinned entries are all reported in the error.
        
        Scenario: Multiple unpinned BaseOS entries
          Given a catalog with multiple BaseOS entries missing versions
          When validate_base_os_version_pinning is called
          Then a BaseOSVersionNotPinnedError is raised
          And all unpinned entries are listed in the error
        """
        # Arrange
        catalog = Catalog(
            identifier="test-catalog",
            version="1.0",
            schema_version=2,
            name="Test Catalog",
            base_os=[
                {"Name": "rhel"},  # Missing Version
                {"Name": "kernel"},  # Missing Version
                {"Version": "1.0"},  # Missing Name
            ],
            functional_layer=[],
            infrastructure=[],
            drivers_layer=[],
            drivers=[],
            functional_packages=[],
            os_packages=[],
            infrastructure_packages=[],
            miscellaneous=[],
        )

        # Act & Assert
        with pytest.raises(BaseOSVersionNotPinnedError) as exc_info:
            validate_base_os_version_pinning(catalog)

        # Verify all unpinned entries are reported
        unpinned = exc_info.value.unpinned_entries
        assert "rhel" in unpinned
        assert "kernel" in unpinned
        assert "BaseOS[2] (unnamed)" in unpinned


# ---------------------------------------------------------------------------
# TC-UT-006: Extract Base OS Versions for Pulp Validation
# ---------------------------------------------------------------------------

class TestExtractBaseOSVersions:
    """Test cases for extracting base OS versions for Pulp validation."""

    def test_extract_base_os_versions_success(self, valid_catalog_with_pinned_os):
        """Extract (name, version) pairs from catalog BaseOS layer.
        
        Scenario: Extract base OS versions for Pulp validation
          Given a catalog with pinned BaseOS entries
          When extract_base_os_versions is called
          Then a list of (os_name, os_version) tuples is returned
          And the list contains ("rhel", "10.0")
          And the list contains ("kernel", "5.14.0")
        """
        # Act
        os_versions = extract_base_os_versions(valid_catalog_with_pinned_os)

        # Assert
        assert os_versions == [
            ("rhel", "10.0"),
            ("kernel", "5.14.0"),
        ]

    def test_extract_base_os_versions_empty_list(self, catalog_with_empty_base_os):
        """Extract from empty BaseOS returns empty list.
        
        Scenario: Extract from empty BaseOS
          Given a catalog with an empty BaseOS array
          When extract_base_os_versions is called
          Then an empty list is returned
        """
        # Act
        os_versions = extract_base_os_versions(catalog_with_empty_base_os)

        # Assert
        assert os_versions == []

    def test_extract_base_os_versions_with_unpinned_entries(
        self, catalog_with_missing_version
    ):
        """Extract skips entries with missing fields.
        
        Scenario: Extract from catalog with unpinned entries
          Given a catalog with some BaseOS entries missing Version
          When extract_base_os_versions is called
          Then only entries with both Name and Version are included
        """
        # Act
        os_versions = extract_base_os_versions(catalog_with_missing_version)

        # Assert
        # Only the kernel entry has both Name and Version
        assert os_versions == [("kernel", "5.14.0")]
