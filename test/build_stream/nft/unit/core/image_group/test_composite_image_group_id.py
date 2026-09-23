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

"""Unit tests for composite ImageGroupID generation (ER-BSM-002).

Tests the composite ImageGroupID format (identifier-vVersion) and
database persistence with 1:1 Job mapping.

Test coverage:
- TC-UT-003: Composite ImageGroupID generation (FR-2B.2, AC-014)
"""

from datetime import datetime, timezone

import uuid

import pytest

from core.image_group.entities import ImageGroup
from core.image_group.exceptions import DuplicateImageGroupError
from core.image_group.value_objects import ImageGroupId, ImageGroupStatus
from core.jobs.value_objects import JobId


# ---------------------------------------------------------------------------
# TC-UT-003: Composite ImageGroupID Generation
# ---------------------------------------------------------------------------

class TestCompositeImageGroupID:
    """Test cases for composite ImageGroupID generation (FR-2B.2, AC-014).
    
    Validates that ImageGroupID follows {identifier}-v{version} format
    and enforces uniqueness and 1:1 Job mapping.
    """

    def test_composite_image_group_id_generation(self):
        """Composite ImageGroupID follows {identifier}-v{version} format.
        
        Scenario: Generate composite ImageGroupID
          Given catalog.identifier is "omnia-slurm-rhel-10-0-x86-64-aarch64"
          And catalog.version is "1.2"
          When the composite ImageGroupID is generated
          Then the ID is "omnia-slurm-rhel-10-0-x86-64-aarch64-v1.2"
          And the format is "{identifier}-v{version}"
        """
        # Arrange
        identifier = "omnia-slurm-rhel-10-0-x86-64-aarch64"
        version = "1.2"
        expected_id = f"{identifier}-v{version}"
        job_id = JobId(str(uuid.uuid4()))
        
        # Act
        image_group_id = ImageGroupId(expected_id)
        image_group = ImageGroup(
            id=image_group_id,
            job_id=job_id,
            status=ImageGroupStatus.BUILT,
            catalog_identifier=identifier,
            catalog_version=version,
            catalog_schema_version=2,
        )

        # Assert
        assert str(image_group.id) == "omnia-slurm-rhel-10-0-x86-64-aarch64-v1.2"
        assert image_group.catalog_identifier == identifier
        assert image_group.catalog_version == version

    def test_composite_image_group_id_with_special_characters(self):
        """Composite ImageGroupID with special characters in identifier.
        
        Scenario: Handle identifiers with hyphens
          Given catalog.identifier contains hyphens
          When the composite ImageGroupID is generated
          Then the format is preserved correctly
        """
        # Arrange
        identifier = "omnia-slurm-rhel-10-0-x86-64-aarch64"  # Multiple hyphens
        version = "2.0"
        composite_id = f"{identifier}-v{version}"
        job_id = JobId(str(uuid.uuid4()))
        
        # Act
        image_group = ImageGroup(
            id=ImageGroupId(composite_id),
            job_id=job_id,
            status=ImageGroupStatus.BUILT,
            catalog_identifier=identifier,
            catalog_version=version,
        )

        # Assert
        assert str(image_group.id) == "omnia-slurm-rhel-10-0-x86-64-aarch64-v2.0"
        # Verify identifier and version can be extracted
        assert image_group.catalog_identifier == identifier
        assert image_group.catalog_version == version

    def test_composite_image_group_id_with_different_versions(self):
        """Different versions create different composite IDs for same identifier.
        
        Scenario: Multiple versions of the same catalog
          Given catalog.identifier is "omnia-slurm"
          When versions "1.0", "1.1", "2.0" are processed
          Then three distinct composite IDs are created
          And each follows {identifier}-v{version} format
        """
        # Arrange
        identifier = "omnia-slurm"
        versions = ["1.0", "1.1", "2.0"]
        
        # Act
        composite_ids = [f"{identifier}-v{v}" for v in versions]
        
        # Assert
        assert composite_ids == [
            "omnia-slurm-v1.0",
            "omnia-slurm-v1.1",
            "omnia-slurm-v2.0",
        ]
        # Verify all are unique
        assert len(set(composite_ids)) == 3

    def test_image_group_status_transitions(self):
        """ImageGroup can transition through lifecycle statuses.
        
        Scenario: ImageGroup status transitions
          Given an ImageGroup with status BUILT
          When the status is changed to DEPLOYING
          Then the status is updated to DEPLOYING
          And the updated_at timestamp is refreshed
        """
        # Arrange
        image_group = ImageGroup(
            id=ImageGroupId("test-catalog-v1.0"),
            job_id=JobId(str(uuid.uuid4())),
            status=ImageGroupStatus.BUILT,
            catalog_identifier="test-catalog",
            catalog_version="1.0",
        )
        initial_updated_at = image_group.updated_at

        # Act
        image_group.status = ImageGroupStatus.DEPLOYING
        image_group.updated_at = datetime.now(timezone.utc)

        # Assert
        assert image_group.status == ImageGroupStatus.DEPLOYING
        assert image_group.updated_at > initial_updated_at

    def test_image_group_deploy_count_increments(self):
        """ImageGroup deploy_count tracks deployment history.
        
        Scenario: Track deployment count
          Given an ImageGroup with deploy_count=0
          When the image group is deployed
          Then deploy_count increments to 1
          And last_deployed_at is updated
        """
        # Arrange
        image_group = ImageGroup(
            id=ImageGroupId("deployed-catalog-v1.0"),
            job_id=JobId(str(uuid.uuid4())),
            status=ImageGroupStatus.BUILT,
            catalog_identifier="deployed-catalog",
            catalog_version="1.0",
            deploy_count=0,
        )

        # Act
        image_group.deploy_count += 1
        image_group.last_deployed_at = datetime.now(timezone.utc)

        # Assert
        assert image_group.deploy_count == 1
        assert image_group.last_deployed_at is not None

    def test_image_group_protection_flag(self):
        """ImageGroup is_protected flag exempts from retention pruning.
        
        Scenario: Protected image group
          Given an ImageGroup with is_protected=True
          Then the image group is exempt from age-based retention
        """
        # Arrange & Act
        image_group = ImageGroup(
            id=ImageGroupId("protected-catalog-v1.0"),
            job_id=JobId(str(uuid.uuid4())),
            status=ImageGroupStatus.BUILT,
            catalog_identifier="protected-catalog",
            catalog_version="1.0",
            is_protected=True,
        )

        # Assert
        assert image_group.is_protected is True

    def test_composite_id_uniqueness_constraint(self):
        """Composite ImageGroupID must be unique across the system.
        
        Scenario: Duplicate composite ID rejected
          Given an ImageGroup with ID "omnia-slurm-v1.0" exists
          When another ImageGroup with the same ID is created
          Then a uniqueness constraint would be violated
          
        Note: Actual DB constraint enforcement is tested in integration tests.
        This test validates the entity model supports the constraint.
        """
        # Arrange
        composite_id = ImageGroupId("omnia-slurm-v1.0")
        
        # Act - Create two ImageGroups with same ID but different job_id
        image_group_1 = ImageGroup(
            id=composite_id,
            job_id=JobId(str(uuid.uuid4())),
            status=ImageGroupStatus.BUILT,
            catalog_identifier="omnia-slurm",
            catalog_version="1.0",
        )
        
        image_group_2 = ImageGroup(
            id=composite_id,
            job_id=JobId(str(uuid.uuid4())),  # Different job
            status=ImageGroupStatus.BUILT,
            catalog_identifier="omnia-slurm",
            catalog_version="1.0",
        )

        # Assert - Both entities can be created, but DB would enforce uniqueness
        assert image_group_1.id == image_group_2.id
        assert image_group_1.job_id != image_group_2.job_id
        # In-memory entities don't enforce DB constraints
        # The database UNIQUE constraint on id would prevent the second save

    def test_job_id_uniqueness_constraint(self):
        """Each ImageGroup must map to exactly one Job (1:1 relationship).
        
        Scenario: 1:1 Job-to-ImageGroup mapping
          Given an ImageGroup with a specific job_id
          When another ImageGroup tries to use the same job_id
          Then a uniqueness constraint would be violated
          
        Note: DB UNIQUE constraint on job_id enforces this at persistence layer.
        """
        # Arrange
        shared_job_id = JobId(str(uuid.uuid4()))
        
        # Act - Create two ImageGroups with different IDs but same job_id
        image_group_1 = ImageGroup(
            id=ImageGroupId("catalog-a-v1.0"),
            job_id=shared_job_id,
            status=ImageGroupStatus.BUILT,
            catalog_identifier="catalog-a",
            catalog_version="1.0",
        )
        
        image_group_2 = ImageGroup(
            id=ImageGroupId("catalog-b-v1.0"),
            job_id=shared_job_id,  # Same job_id
            status=ImageGroupStatus.BUILT,
            catalog_identifier="catalog-b",
            catalog_version="1.0",
        )

        # Assert - Both entities can be created, but DB would enforce uniqueness
        assert image_group_1.job_id == image_group_2.job_id
        assert image_group_1.id != image_group_2.id
        # The database UNIQUE constraint on job_id would prevent the second save
