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

"""Unit tests for InMemoryImageGroupRepository and InMemoryImageRepository."""

import uuid
from datetime import datetime, timezone

import pytest

from build_stream.core.image_group.entities import ImageGroup, Image
from build_stream.core.image_group.value_objects import (
    ImageGroupId,
    ImageGroupStatus,
)
from build_stream.core.jobs.value_objects import JobId
from build_stream.infra.repositories.in_memory import (
    InMemoryImageGroupRepository,
    InMemoryImageRepository,
)


def _make_job_id() -> JobId:
    return JobId(str(uuid.uuid4()))


def _make_image_group(
    ig_id: str = "test-group",
    job_id: JobId = None,
    status: ImageGroupStatus = ImageGroupStatus.BUILT,
) -> ImageGroup:
    return ImageGroup(
        id=ImageGroupId(ig_id),
        job_id=job_id or _make_job_id(),
        status=status,
    )


class TestInMemoryImageGroupRepository:
    """Tests for InMemoryImageGroupRepository."""

    def test_save_and_find_by_id(self):
        """save() then find_by_id() should return the same entity."""
        repo = InMemoryImageGroupRepository()
        ig = _make_image_group()
        repo.save(ig)
        found = repo.find_by_id(ig.id)
        assert found is not None
        assert found.id == ig.id

    def test_find_by_id_not_found(self):
        """find_by_id() should return None for non-existent ID."""
        repo = InMemoryImageGroupRepository()
        result = repo.find_by_id(ImageGroupId("nonexistent"))
        assert result is None

    def test_find_by_job_id(self):
        """find_by_job_id() should return ImageGroup for matching job."""
        repo = InMemoryImageGroupRepository()
        job_id = _make_job_id()
        ig = _make_image_group(job_id=job_id)
        repo.save(ig)
        found = repo.find_by_job_id(job_id)
        assert found is not None
        assert str(found.job_id) == str(job_id)

    def test_find_by_job_id_not_found(self):
        """find_by_job_id() should return None for non-matching job."""
        repo = InMemoryImageGroupRepository()
        result = repo.find_by_job_id(_make_job_id())
        assert result is None

    def test_find_by_job_id_for_update(self):
        """find_by_job_id_for_update() should behave like find_by_job_id in memory."""
        repo = InMemoryImageGroupRepository()
        job_id = _make_job_id()
        ig = _make_image_group(job_id=job_id)
        repo.save(ig)
        found = repo.find_by_job_id_for_update(job_id)
        assert found is not None
        assert str(found.job_id) == str(job_id)

    def test_update_status(self):
        """update_status() should change the status and update timestamp."""
        repo = InMemoryImageGroupRepository()
        ig = _make_image_group(status=ImageGroupStatus.BUILT)
        repo.save(ig)

        repo.update_status(ig.id, ImageGroupStatus.DEPLOYING)

        updated = repo.find_by_id(ig.id)
        assert updated is not None
        assert updated.status == ImageGroupStatus.DEPLOYING

    def test_update_status_nonexistent(self):
        """update_status() on non-existent ID should not raise."""
        repo = InMemoryImageGroupRepository()
        repo.update_status(ImageGroupId("nonexistent"), ImageGroupStatus.BUILT)

    def test_list_by_status(self):
        """list_by_status() should filter by status and paginate."""
        repo = InMemoryImageGroupRepository()
        for i in range(5):
            repo.save(_make_image_group(ig_id=f"built-{i}", status=ImageGroupStatus.BUILT))
        for i in range(3):
            repo.save(_make_image_group(ig_id=f"deployed-{i}", status=ImageGroupStatus.DEPLOYED))

        built_groups, total = repo.list_by_status(ImageGroupStatus.BUILT, limit=10, offset=0)
        assert total == 5
        assert len(built_groups) == 5

        deployed_groups, total = repo.list_by_status(ImageGroupStatus.DEPLOYED, limit=10, offset=0)
        assert total == 3
        assert len(deployed_groups) == 3

    def test_list_by_status_pagination(self):
        """list_by_status() should respect limit and offset."""
        repo = InMemoryImageGroupRepository()
        for i in range(5):
            repo.save(_make_image_group(ig_id=f"group-{i}", status=ImageGroupStatus.BUILT))

        page1, total = repo.list_by_status(ImageGroupStatus.BUILT, limit=2, offset=0)
        assert total == 5
        assert len(page1) == 2

        page2, total = repo.list_by_status(ImageGroupStatus.BUILT, limit=2, offset=2)
        assert total == 5
        assert len(page2) == 2

        page3, total = repo.list_by_status(ImageGroupStatus.BUILT, limit=2, offset=4)
        assert total == 5
        assert len(page3) == 1

    def test_exists_true(self):
        """exists() should return True for saved ImageGroup."""
        repo = InMemoryImageGroupRepository()
        ig = _make_image_group()
        repo.save(ig)
        assert repo.exists(ig.id) is True

    def test_exists_false(self):
        """exists() should return False for non-existent ImageGroup."""
        repo = InMemoryImageGroupRepository()
        assert repo.exists(ImageGroupId("nonexistent")) is False


class TestInMemoryImageRepository:
    """Tests for InMemoryImageRepository."""

    def test_save_batch_and_find(self):
        """save_batch() then find_by_image_group_id() should return saved images."""
        repo = InMemoryImageRepository()
        images = [
            Image(
                id=str(uuid.uuid4()),
                image_group_id="group-1",
                role="slurm_node",
                image_name="slurm_node.img",
            ),
            Image(
                id=str(uuid.uuid4()),
                image_group_id="group-1",
                role="kube_node",
                image_name="kube_node.img",
            ),
        ]
        repo.save_batch(images)

        found = repo.find_by_image_group_id(ImageGroupId("group-1"))
        assert len(found) == 2
        roles = {img.role for img in found}
        assert roles == {"slurm_node", "kube_node"}

    def test_find_by_image_group_id_empty(self):
        """find_by_image_group_id() should return empty list for no matches."""
        repo = InMemoryImageRepository()
        found = repo.find_by_image_group_id(ImageGroupId("nonexistent"))
        assert found == []

    def test_separate_groups(self):
        """Images from different groups should be isolated."""
        repo = InMemoryImageRepository()
        repo.save_batch([
            Image(id=str(uuid.uuid4()), image_group_id="group-a", role="role1", image_name="img1"),
        ])
        repo.save_batch([
            Image(id=str(uuid.uuid4()), image_group_id="group-b", role="role2", image_name="img2"),
        ])

        group_a = repo.find_by_image_group_id(ImageGroupId("group-a"))
        group_b = repo.find_by_image_group_id(ImageGroupId("group-b"))
        assert len(group_a) == 1
        assert len(group_b) == 1
        assert group_a[0].role == "role1"
        assert group_b[0].role == "role2"
