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

"""Domain services for Build Image module."""

import logging
from typing import Optional

from core.build_image.entities import BuildImageRequest
from core.build_image.exceptions import InventoryHostMissingError
from core.build_image.repositories import BuildStreamConfigRepository
from core.build_image.value_objects import Architecture, InventoryHost
from core.jobs.value_objects import CorrelationId

logger = logging.getLogger(__name__)


class BuildImageConfigService:
    """Service for build image configuration operations."""

    def __init__(self, config_repo: BuildStreamConfigRepository):
        """Initialize service with repository."""
        self._config_repo = config_repo

    def get_inventory_host(
        self, job_id: str, architecture: Architecture, correlation_id: str
    ) -> Optional[InventoryHost]:
        """Get inventory host for aarch64 builds.

        Args:
            job_id: Job identifier.
            architecture: Target architecture.
            correlation_id: Correlation ID for error reporting.

        Returns:
            Inventory host for aarch64, None for x86_64.

        Raises:
            InventoryHostMissingError: If aarch64 and no host configured.
        """
        if architecture.is_x86_64:
            return None

        # For aarch64, inventory host is required
        inventory_host = self._config_repo.get_aarch64_inv_host(job_id)
        if not inventory_host:
            raise InventoryHostMissingError(
                "Inventory host is required for aarch64 builds", correlation_id
            )
        return inventory_host


class BuildImageQueueService:
    """Service for build image queue operations."""

    def __init__(self, queue_repo):
        """Initialize service with PlaybookQueueRequestRepository."""
        self._queue_repo = queue_repo

    def submit_request(self, request: BuildImageRequest, correlation_id: CorrelationId):
        """Submit build image request to queue.

        Args:
            request: BuildImageRequest to submit.
            correlation_id: Correlation ID for tracing.

        Raises:
            QueueUnavailableError: If queue is not accessible.
        """
        logger.info(
            "Submitting build image request to queue: job_id=%s, correlation_id=%s",
            request.job_id,
            correlation_id,
        )
        self._queue_repo.write_request(request)
        logger.info(
            "Build image request submitted successfully: job_id=%s, "
            "request_id=%s, correlation_id=%s",
            request.job_id,
            request.request_id,
            correlation_id,
        )
