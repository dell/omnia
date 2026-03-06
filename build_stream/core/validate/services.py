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

"""Domain services for ValidateImageOnTest module."""

import logging

from core.jobs.value_objects import CorrelationId
from core.validate.entities import ValidateImageOnTestRequest

logger = logging.getLogger(__name__)


class ValidateQueueService:
    """Service for validate-image-on-test queue operations."""

    def __init__(self, queue_repo) -> None:
        """Initialize service with PlaybookQueueRequestRepository.

        Args:
            queue_repo: Playbook queue request repository implementation.
        """
        self._queue_repo = queue_repo

    def submit_request(
        self,
        request: ValidateImageOnTestRequest,
        correlation_id: CorrelationId,
    ) -> None:
        """Submit validate-image-on-test request to queue.

        Args:
            request: ValidateImageOnTestRequest to submit.
            correlation_id: Correlation ID for tracing.

        Raises:
            QueueUnavailableError: If queue is not accessible.
        """
        logger.info(
            "Submitting validate-image-on-test request to queue: "
            "job_id=%s, correlation_id=%s",
            request.job_id,
            correlation_id,
        )
        self._queue_repo.write_request(request)
        logger.info(
            "Validate-image-on-test request submitted successfully: "
            "job_id=%s, request_id=%s, correlation_id=%s",
            request.job_id,
            request.request_id,
            correlation_id,
        )
