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

"""Result poller for processing playbook execution results from NFS queue."""

import asyncio
import logging
from datetime import datetime, timezone

from api.logging_utils import log_secure_info

from core.jobs.entities import AuditEvent
from core.jobs.repositories import (
    AuditEventRepository,
    StageRepository,
    UUIDGenerator,
)
from core.jobs.value_objects import StageName
from core.localrepo.entities import PlaybookResult
from core.localrepo.services import PlaybookQueueResultService

logger = logging.getLogger(__name__)


class LocalRepoResultPoller:
    """Poller for processing playbook execution results.
    
    This poller monitors the NFS result queue and processes results
    by updating stage states and emitting audit events.
    
    Attributes:
        result_service: Service for polling NFS result queue.
        stage_repo: Stage repository for updating stage states.
        audit_repo: Audit event repository for emitting events.
        uuid_generator: UUID generator for event IDs.
        poll_interval: Interval in seconds between polls.
        running: Flag indicating if poller is running.
    """

    def __init__(
        self,
        result_service: PlaybookQueueResultService,
        stage_repo: StageRepository,
        audit_repo: AuditEventRepository,
        uuid_generator: UUIDGenerator,
        poll_interval: int = 5,
    ) -> None:  # pylint: disable=too-many-arguments,too-many-positional-arguments
        """Initialize result poller.
        
        Args:
            result_service: Service for polling NFS result queue.
            stage_repo: Stage repository implementation.
            audit_repo: Audit event repository implementation.
            uuid_generator: UUID generator for identifiers.
            poll_interval: Interval in seconds between polls (default: 5).
        """
        self._result_service = result_service
        self._stage_repo = stage_repo
        self._audit_repo = audit_repo
        self._uuid_generator = uuid_generator
        self._poll_interval = poll_interval
        self._running = False
        self._task = None

    async def start(self) -> None:
        """Start the result poller."""
        if self._running:
            logger.warning("Result poller is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Result poller started with interval=%ds", self._poll_interval)

    async def stop(self) -> None:
        """Stop the result poller."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Result poller stopped")

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                processed_count = self._result_service.poll_results(
                    callback=self._on_result_received
                )
                if processed_count > 0:
                    logger.info("Processed %d playbook results", processed_count)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Error polling results: %s", exc)

            await asyncio.sleep(self._poll_interval)

    def _on_result_received(self, result: PlaybookResult) -> None:
        """Handle received playbook result.
        
        Args:
            result: Playbook execution result from NFS queue.
        """
        try:
            # Find stage
            stage_name = StageName(result.stage_name)
            stage = self._stage_repo.find_by_job_and_name(result.job_id, stage_name)

            if stage is None:
                logger.error(
                    "Stage not found for result: job_id=%s, stage=%s",
                    result.job_id,
                    result.stage_name,
                )
                return

            # Update stage based on result
            if result.status == "success":
                stage.complete()
                logger.info(
                    "Stage completed successfully: job_id=%s, stage=%s",
                    result.job_id,
                    result.stage_name,
                )
            else:
                error_code = result.error_code or "PLAYBOOK_FAILED"
                error_summary = result.error_summary or "Playbook execution failed"
                stage.fail(error_code=error_code, error_summary=error_summary)
                logger.warning(
                    "Stage failed: job_id=%s, stage=%s, error=%s",
                    result.job_id,
                    result.stage_name,
                    error_code,
                )

            # Save updated stage
            self._stage_repo.save(stage)

            # Emit audit event
            event = AuditEvent(
                event_id=str(self._uuid_generator.generate()),
                job_id=result.job_id,
                event_type="STAGE_COMPLETED" if result.status == "success" else "STAGE_FAILED",
                correlation_id=result.request_id,
                client_id=result.job_id,  # Using job_id as client_id placeholder
                timestamp=datetime.now(timezone.utc),
                details={
                    "stage_name": result.stage_name,
                    "status": result.status,
                    "duration_seconds": result.duration_seconds,
                    "exit_code": result.exit_code,
                },
            )
            self._audit_repo.save(event)

            log_secure_info(
                "info",
                f"Result processed for job {result.job_id}, stage {result.stage_name}",
                result.request_id,
            )

        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Error handling result: job_id=%s, error=%s",
                result.job_id,
                exc,
            )
