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

"""Unit tests for ImageGroup and Image domain entities."""

import uuid
from datetime import datetime, timezone

import pytest

from build_stream.core.image_group.entities import ImageGroup, Image
from build_stream.core.image_group.value_objects import (
    ImageGroupId,
    ImageGroupStatus,
)
from build_stream.core.jobs.value_objects import JobId


def _make_job_id() -> JobId:
    """Generate a valid JobId for testing."""
    return JobId(str(uuid.uuid4()))


def _make_image_group(
    ig_id: str = "test-group-v1",
    status: ImageGroupStatus = ImageGroupStatus.BUILT,
) -> ImageGroup:
    """Create an ImageGroup for testing."""
    return ImageGroup(
        id=ImageGroupId(ig_id),
        job_id=_make_job_id(),
        status=status,
    )


class TestImageGroup:
    """Tests for ImageGroup domain entity."""

    def test_creation_with_defaults(self):
        """ImageGroup should initialize with default timestamps and empty images."""
        ig = _make_image_group()
        assert ig.id.value == "test-group-v1"
        assert ig.status == ImageGroupStatus.BUILT
        assert ig.images == []
        assert ig.created_at is not None
        assert ig.updated_at is not None

    def test_creation_with_explicit_values(self):
        """ImageGroup should accept explicit values."""
        job_id = _make_job_id()
        now = datetime.now(timezone.utc)
        ig = ImageGroup(
            id=ImageGroupId("explicit-group"),
            job_id=job_id,
            status=ImageGroupStatus.DEPLOYED,
            images=[],
            created_at=now,
            updated_at=now,
        )
        assert ig.id.value == "explicit-group"
        assert ig.job_id == job_id
        assert ig.status == ImageGroupStatus.DEPLOYED
        assert ig.created_at == now

    def test_transition_status(self):
        """transition_status should update status and timestamp."""
        ig = _make_image_group(status=ImageGroupStatus.BUILT)
        old_updated_at = ig.updated_at

        ig.transition_status(ImageGroupStatus.DEPLOYING)

        assert ig.status == ImageGroupStatus.DEPLOYING
        assert ig.updated_at >= old_updated_at

    def test_transition_status_full_lifecycle(self):
        """ImageGroup should support the full deploy lifecycle."""
        ig = _make_image_group(status=ImageGroupStatus.BUILT)

        transitions = [
            ImageGroupStatus.DEPLOYING,
            ImageGroupStatus.DEPLOYED,
            ImageGroupStatus.RESTARTING,
            ImageGroupStatus.RESTARTED,
            ImageGroupStatus.VALIDATING,
            ImageGroupStatus.PASSED,
        ]

        for target_status in transitions:
            ig.transition_status(target_status)
            assert ig.status == target_status

    def test_images_list_mutable(self):
        """The images list should be mutable for adding images."""
        ig = _make_image_group()
        image = Image(
            id=str(uuid.uuid4()),
            image_group_id="test-group-v1",
            role="slurm_node",
            image_name="slurm_node.img",
        )
        ig.images.append(image)
        assert len(ig.images) == 1
        assert ig.images[0].role == "slurm_node"


class TestImage:
    """Tests for Image domain entity."""

    def test_creation_with_defaults(self):
        """Image should initialize with default timestamp."""
        img = Image(
            id=str(uuid.uuid4()),
            image_group_id="test-group",
            role="slurm_node",
            image_name="slurm_node.img",
        )
        assert img.role == "slurm_node"
        assert img.image_name == "slurm_node.img"
        assert img.created_at is not None

    def test_creation_with_explicit_timestamp(self):
        """Image should accept explicit timestamp."""
        now = datetime.now(timezone.utc)
        img = Image(
            id="test-id",
            image_group_id="test-group",
            role="kube_node",
            image_name="kube_node.img",
            created_at=now,
        )
        assert img.created_at == now

    def test_immutability(self):
        """Image should be immutable (frozen dataclass)."""
        img = Image(
            id="test-id",
            image_group_id="test-group",
            role="slurm_node",
            image_name="slurm_node.img",
        )
        with pytest.raises(AttributeError):
            img.role = "other_role"

    def test_equality(self):
        """Two Images with same attributes should be equal."""
        now = datetime.now(timezone.utc)
        img1 = Image(
            id="same-id",
            image_group_id="group",
            role="node",
            image_name="node.img",
            created_at=now,
        )
        img2 = Image(
            id="same-id",
            image_group_id="group",
            role="node",
            image_name="node.img",
            created_at=now,
        )
        assert img1 == img2

    def test_multiple_roles(self):
        """Different roles within the same group should be separate entities."""
        group_id = "test-group"
        roles = ["slurm_node", "kube_control_plane", "login_node", "nfs_node"]
        images = [
            Image(
                id=str(uuid.uuid4()),
                image_group_id=group_id,
                role=role,
                image_name=f"{role}.img",
            )
            for role in roles
        ]
        assert len(images) == 4
        assert len({img.role for img in images}) == 4
