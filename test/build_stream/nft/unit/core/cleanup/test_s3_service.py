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

"""Unit tests for Cleanup S3 service interface and value objects."""

import pytest

from core.cleanup.s3_service import S3CleanupResult, S3CleanupService


class TestS3CleanupResult:
    """Tests for S3CleanupResult value object."""

    def test_create_success_result(self):
        """Should create a successful result."""
        result = S3CleanupResult(
            image_path="s3://boot-images/slurm_node/img-001/",
            objects_deleted=5,
            exit_code=0,
            success=True,
        )
        assert result.image_path == "s3://boot-images/slurm_node/img-001/"
        assert result.objects_deleted == 5
        assert result.exit_code == 0
        assert result.success is True

    def test_create_failure_result(self):
        """Should create a failure result."""
        result = S3CleanupResult(
            image_path="s3://boot-images/bad-path/",
            objects_deleted=0,
            exit_code=1,
            success=False,
        )
        assert result.success is False
        assert result.exit_code == 1
        assert result.objects_deleted == 0

    def test_immutability(self):
        """Result should be immutable (frozen dataclass)."""
        result = S3CleanupResult(
            image_path="s3://test", objects_deleted=0, exit_code=0, success=True
        )
        with pytest.raises(AttributeError):
            result.success = False

    def test_zero_objects_deleted(self):
        """Should handle zero objects deleted (empty prefix)."""
        result = S3CleanupResult(
            image_path="s3://boot-images/empty/",
            objects_deleted=0,
            exit_code=0,
            success=True,
        )
        assert result.objects_deleted == 0
        assert result.success is True


class TestS3CleanupServiceInterface:
    """Tests for S3CleanupService abstract interface."""

    def test_is_abstract(self):
        """S3CleanupService should be abstract and not instantiable."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            S3CleanupService()

    def test_subclass_must_implement_delete(self):
        """Subclass that doesn't implement delete_image_path should fail."""
        class IncompleteService(S3CleanupService):
            pass

        with pytest.raises(TypeError):
            IncompleteService()

    def test_concrete_subclass_works(self):
        """Concrete subclass implementing delete_image_path should instantiate."""
        class FakeService(S3CleanupService):
            def delete_image_path(self, image_path: str) -> S3CleanupResult:
                return S3CleanupResult(
                    image_path=image_path,
                    objects_deleted=1,
                    exit_code=0,
                    success=True,
                )

        service = FakeService()
        result = service.delete_image_path("s3://boot-images/test/")
        assert result.success is True
        assert result.objects_deleted == 1
