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

"""Repository port interfaces for ImageGroup domain.

These define the contracts that infrastructure implementations must satisfy.
Using ABC for explicit interface definition.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from core.image_group.entities import ImageGroup, Image
from core.image_group.value_objects import ImageGroupId, ImageGroupStatus
from core.jobs.value_objects import JobId


class ImageGroupRepository(ABC):
    """Abstract repository for ImageGroup persistence.

    Implementations: SqlImageGroupRepository (prod), InMemoryImageGroupRepository (dev).
    """

    @abstractmethod
    def save(self, image_group: ImageGroup) -> None:
        """Persist a new ImageGroup record.

        Args:
            image_group: ImageGroup entity to persist.
        """
        ...

    @abstractmethod
    def find_by_id(self, image_group_id: ImageGroupId) -> Optional[ImageGroup]:
        """Find ImageGroup by its catalog ID.

        Args:
            image_group_id: Catalog identifier.

        Returns:
            ImageGroup if found, None otherwise.
        """
        ...

    @abstractmethod
    def find_by_job_id(self, job_id: JobId) -> Optional[ImageGroup]:
        """Find ImageGroup by associated Job ID (1:1 mapping).

        Args:
            job_id: Associated job identifier.

        Returns:
            ImageGroup if found, None otherwise.
        """
        ...

    @abstractmethod
    def find_by_job_id_for_update(self, job_id: JobId) -> Optional[ImageGroup]:
        """Find ImageGroup with row-level lock (SELECT FOR UPDATE).

        Used by deploy/restart/validate stages to prevent concurrent
        status transitions.

        Args:
            job_id: Associated job identifier.

        Returns:
            ImageGroup if found, None otherwise.
        """
        ...

    @abstractmethod
    def update_status(
        self, image_group_id: ImageGroupId, new_status: ImageGroupStatus
    ) -> None:
        """Update ImageGroup status and updated_at timestamp.

        Args:
            image_group_id: Identifier of the ImageGroup.
            new_status: Target status.
        """
        ...

    @abstractmethod
    def list_by_status(
        self,
        status: ImageGroupStatus,
        limit: int,
        offset: int,
    ) -> Tuple[List[ImageGroup], int]:
        """List ImageGroups by status with pagination.

        Args:
            status: Filter by this status.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            Tuple of (image_groups_with_images, total_count).
        """
        ...

    @abstractmethod
    def exists(self, image_group_id: ImageGroupId) -> bool:
        """Check if an ImageGroup with the given ID exists.

        Args:
            image_group_id: Identifier to check.

        Returns:
            True if exists, False otherwise.
        """
        ...


class ImageRepository(ABC):
    """Abstract repository for Image persistence."""

    @abstractmethod
    def save_batch(self, images: List[Image]) -> None:
        """Persist multiple Image records in a single operation.

        Args:
            images: List of Image entities to persist.
        """
        ...

    @abstractmethod
    def find_by_image_group_id(
        self, image_group_id: ImageGroupId
    ) -> List[Image]:
        """Find all Images belonging to an ImageGroup.

        Args:
            image_group_id: Parent ImageGroup identifier.

        Returns:
            List of Image entities (may be empty).
        """
        ...
