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

"""ImageGroup and Image domain entities."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from core.image_group.value_objects import ImageGroupId, ImageGroupStatus
from core.jobs.value_objects import JobId


@dataclass
class ImageGroup:
    """ImageGroup domain entity.

    Tracks the lifecycle of a built image group from catalog parsing
    through deploy, restart, validate, and cleanup.

    The 1:1 relationship with Job is enforced at the DB level via
    UNIQUE constraint on job_id.

    Attributes:
        id: Composite ImageGroupID (``identifier-vVersion``).
        job_id: Associated job (1:1 mapping).
        status: Current lifecycle status.
        catalog_identifier: Catalog identifier string.
        catalog_version: Catalog version string.
        catalog_schema_version: Structural schema version (integer).
        deploy_count: Number of times this image group has been deployed.
        is_protected: Whether this image group is protected from retention.
        images: Constituent images within this group.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        last_deployed_at: Timestamp of last deployment.
    """

    id: ImageGroupId
    job_id: JobId
    status: ImageGroupStatus
    catalog_identifier: Optional[str] = None
    catalog_version: Optional[str] = None
    catalog_schema_version: Optional[int] = None
    deploy_count: int = 0
    is_protected: bool = False
    images: List["Image"] = field(default_factory=list)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_deployed_at: Optional[datetime] = None

    def transition_status(self, new_status: ImageGroupStatus) -> None:
        """Transition to a new status and update timestamp.

        Args:
            new_status: The target ImageGroupStatus.
        """
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)


@dataclass(frozen=True)
class Image:
    """Constituent image within an ImageGroup.

    Each image is identified by its functional role (e.g., slurm_node)
    and the generated image file name (e.g., slurm_node.img).

    Attributes:
        id: UUID identifier for this image record.
        image_group_id: FK to parent ImageGroup.
        role: Functional role name (e.g., slurm_node).
        image_name: Generated image file name (e.g., slurm_node.img).
        manifest_path: Path to the sidecar JSON manifest (optional).
        created_at: Creation timestamp.
    """

    id: str
    image_group_id: str
    role: str
    image_name: str
    manifest_path: Optional[str] = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
