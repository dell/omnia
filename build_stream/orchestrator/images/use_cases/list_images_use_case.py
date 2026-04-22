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

"""ListImages use case implementation."""

from typing import Optional

from core.image_group.repositories import ImageGroupRepository
from core.image_group.value_objects import ImageGroupStatus
from api.images.schemas import (
    ImageResponse,
    ImageGroupResponse,
    PaginationResponse,
    ListImagesResponse,
)


class ListImagesUseCase:
    """Orchestrates the Images API query and response assembly."""

    def __init__(self, image_group_repo: ImageGroupRepository):
        self._repo = image_group_repo

    def execute(
        self,
        status: Optional[ImageGroupStatus],
        limit: int,
        offset: int,
    ) -> ListImagesResponse:
        """Query image_groups + images, assemble paginated response.
        
        Args:
            status: Filter by specific status, or None for all post-BUILT states.
            limit: Maximum number of results.
            offset: Number of results to skip.
            
        Returns:
            Paginated list of image groups.
        """
        if status is None:
            # Query all post-BUILT states (cumulative)
            image_groups, total_count = self._repo.list_post_built(
                limit=limit, offset=offset
            )
        else:
            # Query specific status
            image_groups, total_count = self._repo.list_by_status(
                status=status, limit=limit, offset=offset
            )

        group_responses = []
        for ig in image_groups:
            images = [
                ImageResponse(role=img.role, image_name=img.image_name)
                for img in ig.images
            ]
            group_responses.append(
                ImageGroupResponse(
                    job_id=str(ig.job_id),
                    image_group_id=str(ig.id),
                    images=images,
                    status=ig.status.value if hasattr(ig.status, 'value') else str(ig.status),
                    created_at=ig.created_at,
                    updated_at=ig.updated_at,
                )
            )

        pagination = PaginationResponse(
            total_count=total_count,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total_count,
        )

        return ListImagesResponse(
            image_groups=group_responses,
            pagination=pagination,
        )
