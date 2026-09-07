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

"""Unit tests for ListImages use case."""

import uuid
from datetime import datetime, timezone

import pytest

from core.image_group.entities import ImageGroup, Image
from core.image_group.value_objects import ImageGroupId, ImageGroupStatus
from core.jobs.value_objects import JobId
from orchestrator.images.use_cases.list_images_use_case import ListImagesUseCase


def _uuid():
    return str(uuid.uuid4())


class FakeImageGroupRepository:
    """In-memory ImageGroupRepository for testing."""

    def __init__(self):
        self._groups = []

    def add(self, group: ImageGroup):
        self._groups.append(group)

    def list_by_status(self, status, limit, offset):
        filtered = [g for g in self._groups if g.status == status]
        total = len(filtered)
        page = filtered[offset:offset + limit]
        return page, total

    def save(self, image_group):
        self._groups.append(image_group)

    def find_by_id(self, image_group_id):
        for g in self._groups:
            if str(g.id) == str(image_group_id):
                return g
        return None

    def find_by_job_id(self, job_id):
        for g in self._groups:
            if str(g.job_id) == str(job_id):
                return g
        return None

    def find_by_job_id_for_update(self, job_id):
        return self.find_by_job_id(job_id)

    def update_status(self, image_group_id, new_status):
        for g in self._groups:
            if str(g.id) == str(image_group_id):
                g.status = new_status

    def exists(self, image_group_id):
        return any(str(g.id) == str(image_group_id) for g in self._groups)


def _make_image_group(job_id=None, ig_id=None, status=ImageGroupStatus.BUILT, images=None):
    now = datetime.now(timezone.utc)
    return ImageGroup(
        id=ImageGroupId(ig_id or f"test-cluster-{_uuid()[:8]}"),
        job_id=JobId(job_id or _uuid()),
        status=status,
        images=images or [],
        created_at=now,
        updated_at=now,
    )


def _make_image(ig_id, role="slurm_node", image_name="slurm_node.img"):
    return Image(
        id=_uuid(),
        image_group_id=str(ig_id),
        role=role,
        image_name=image_name,
        created_at=datetime.now(timezone.utc),
    )


class TestListImagesUseCase:
    """Tests for ListImagesUseCase."""

    @pytest.fixture
    def repo(self):
        return FakeImageGroupRepository()

    @pytest.fixture
    def use_case(self, repo):
        return ListImagesUseCase(image_group_repo=repo)

    def test_empty_result(self, use_case):
        """Returns empty list and zero count when no groups exist."""
        result = use_case.execute(
            status=ImageGroupStatus.BUILT, limit=100, offset=0
        )
        assert result.image_groups == []
        assert result.pagination.total_count == 0
        assert result.pagination.has_more is False

    def test_returns_built_groups(self, use_case, repo):
        """Returns groups matching the status filter."""
        ig = _make_image_group(status=ImageGroupStatus.BUILT)
        repo.add(ig)

        result = use_case.execute(
            status=ImageGroupStatus.BUILT, limit=100, offset=0
        )
        assert len(result.image_groups) == 1
        assert result.image_groups[0].image_group_id == str(ig.id)
        assert result.image_groups[0].status == "BUILT"
        assert result.pagination.total_count == 1

    def test_filters_by_status(self, use_case, repo):
        """Only returns groups matching the requested status."""
        repo.add(_make_image_group(status=ImageGroupStatus.BUILT))
        repo.add(_make_image_group(status=ImageGroupStatus.DEPLOYED))
        repo.add(_make_image_group(status=ImageGroupStatus.BUILT))

        result = use_case.execute(
            status=ImageGroupStatus.BUILT, limit=100, offset=0
        )
        assert len(result.image_groups) == 2
        assert result.pagination.total_count == 2

    def test_includes_constituent_images(self, use_case, repo):
        """Returns constituent images with each group."""
        ig_id = "test-cluster-v1"
        images = [
            _make_image(ig_id, "slurm_node", "slurm_node.img"),
            _make_image(ig_id, "kube_node", "kube_node.img"),
        ]
        ig = _make_image_group(ig_id=ig_id, images=images)
        repo.add(ig)

        result = use_case.execute(
            status=ImageGroupStatus.BUILT, limit=100, offset=0
        )
        assert len(result.image_groups) == 1
        assert len(result.image_groups[0].images) == 2
        roles = {img.role for img in result.image_groups[0].images}
        assert roles == {"slurm_node", "kube_node"}

    def test_pagination_limit(self, use_case, repo):
        """Respects limit parameter."""
        for _ in range(5):
            repo.add(_make_image_group())

        result = use_case.execute(
            status=ImageGroupStatus.BUILT, limit=2, offset=0
        )
        assert len(result.image_groups) == 2
        assert result.pagination.total_count == 5
        assert result.pagination.limit == 2
        assert result.pagination.has_more is True

    def test_pagination_offset(self, use_case, repo):
        """Respects offset parameter."""
        for _ in range(5):
            repo.add(_make_image_group())

        result = use_case.execute(
            status=ImageGroupStatus.BUILT, limit=100, offset=3
        )
        assert len(result.image_groups) == 2
        assert result.pagination.total_count == 5
        assert result.pagination.offset == 3
        assert result.pagination.has_more is False

    def test_offset_exceeds_total(self, use_case, repo):
        """Returns empty when offset exceeds total count."""
        repo.add(_make_image_group())

        result = use_case.execute(
            status=ImageGroupStatus.BUILT, limit=100, offset=100
        )
        assert len(result.image_groups) == 0
        assert result.pagination.total_count == 1
        assert result.pagination.has_more is False

    def test_has_more_calculation(self, use_case, repo):
        """Correctly calculates has_more flag."""
        for _ in range(3):
            repo.add(_make_image_group())

        # Exact fit — no more
        result = use_case.execute(
            status=ImageGroupStatus.BUILT, limit=3, offset=0
        )
        assert result.pagination.has_more is False

        # More available
        result = use_case.execute(
            status=ImageGroupStatus.BUILT, limit=2, offset=0
        )
        assert result.pagination.has_more is True

    def test_job_id_in_response(self, use_case, repo):
        """Job ID is included in each group response."""
        job_id = _uuid()
        ig = _make_image_group(job_id=job_id)
        repo.add(ig)

        result = use_case.execute(
            status=ImageGroupStatus.BUILT, limit=100, offset=0
        )
        assert result.image_groups[0].job_id == job_id

    def test_group_with_no_images(self, use_case, repo):
        """Returns group with empty images list."""
        ig = _make_image_group(images=[])
        repo.add(ig)

        result = use_case.execute(
            status=ImageGroupStatus.BUILT, limit=100, offset=0
        )
        assert len(result.image_groups) == 1
        assert result.image_groups[0].images == []
