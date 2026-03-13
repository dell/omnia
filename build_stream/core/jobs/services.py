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

"""Domain services for Jobs domain."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from .entities import AuditEvent
from .repositories import JobRepository, AuditEventRepository, UUIDGenerator
from .value_objects import JobId, RequestFingerprint

logger = logging.getLogger(__name__)


class FingerprintService:
    """Domain service for computing request fingerprints.

    Computes deterministic SHA-256 hash of request payload for idempotency.
    """

    @staticmethod
    def compute(request_body: Dict[str, Any]) -> RequestFingerprint:
        """Compute SHA-256 fingerprint of request payload.

        Creates a deterministic hash by:
        1. Sorting keys alphabetically
        2. JSON serializing with no whitespace
        3. UTF-8 encoding
        4. SHA-256 hashing

        Args:
            request_body: Dictionary of request fields.

        Returns:
            RequestFingerprint value object.

        Example:
            >>> body = {"job_id": "123", "client_id": "abc"}
            >>> fp = FingerprintService.compute(body)
            >>> len(fp.value)
            64
        """
        normalized = json.dumps(request_body, sort_keys=True, separators=(',', ':'))
        digest = hashlib.sha256(normalized.encode('utf-8')).hexdigest()
        return RequestFingerprint(digest)


class JobStateHelper:
    """Static utility for centralized job state management.
    
    Provides methods to update job state when stages fail or complete,
    leveraging existing repository dependencies without requiring new services.
    """

    @staticmethod
    def handle_stage_failure(
        job_repo: JobRepository,
        audit_repo: AuditEventRepository,
        uuid_generator: UUIDGenerator,
        job_id: JobId,
        stage_name: str,
        error_code: str,
        error_summary: str,
        correlation_id: str,
        client_id: str,
    ) -> None:
        """Update job state to FAILED when a stage fails.
        
        This method:
        1. Retrieves the job
        2. Transitions job to FAILED state (if not already terminal)
        3. Saves the updated job
        4. Emits JOB_FAILED audit event
        5. Commits sessions if repositories have active sessions
        
        Args:
            job_repo: Job repository for loading/saving jobs.
            audit_repo: Audit repository for emitting events.
            uuid_generator: UUID generator for event IDs.
            job_id: Job identifier.
            stage_name: Name of the failed stage.
            error_code: Error code from stage failure.
            error_summary: Error summary from stage failure.
            correlation_id: Request correlation ID.
            client_id: Client identifier.
        """
        try:
            job = job_repo.find_by_id(job_id)
            if job is None:
                logger.warning(
                    "Job not found when handling stage failure: job_id=%s, stage=%s",
                    job_id, stage_name
                )
                return

            if job.job_state.is_terminal():
                logger.info(
                    "Job already in terminal state: job_id=%s, state=%s, stage=%s",
                    job_id, job.job_state.value, stage_name
                )
                return

            job.fail()
            job_repo.save(job)

            event = AuditEvent(
                event_id=str(uuid_generator.generate()),
                job_id=job_id,
                event_type="JOB_FAILED",
                correlation_id=correlation_id,
                client_id=client_id,
                timestamp=datetime.now(timezone.utc),
                details={
                    "failed_stage": stage_name,
                    "error_code": error_code,
                    "error_summary": error_summary,
                },
            )
            audit_repo.save(event)

            # Commit sessions if repositories have active sessions
            if hasattr(job_repo, 'session') and job_repo.session:
                job_repo.session.commit()
            if hasattr(audit_repo, 'session') and audit_repo.session:
                audit_repo.session.commit()

            logger.info(
                "Job marked as FAILED: job_id=%s, failed_stage=%s, error_code=%s",
                job_id, stage_name, error_code
            )

        except Exception as exc:
            logger.exception(
                "Failed to update job state on stage failure: job_id=%s, stage=%s, error=%s",
                job_id, stage_name, exc
            )

    @staticmethod
    def handle_job_completion(
        job_repo: JobRepository,
        audit_repo: AuditEventRepository,
        uuid_generator: UUIDGenerator,
        job_id: JobId,
        correlation_id: str,
        client_id: str,
    ) -> None:
        """Update job state to COMPLETED when final stage completes.
        
        This method:
        1. Retrieves the job
        2. Transitions job to COMPLETED state (if not already terminal)
        3. Saves the updated job
        4. Emits JOB_COMPLETED audit event
        5. Commits sessions if repositories have active sessions
        
        Args:
            job_repo: Job repository for loading/saving jobs.
            audit_repo: Audit repository for emitting events.
            uuid_generator: UUID generator for event IDs.
            job_id: Job identifier.
            correlation_id: Request correlation ID.
            client_id: Client identifier.
        """
        try:
            job = job_repo.find_by_id(job_id)
            if job is None:
                logger.warning(
                    "Job not found when handling completion: job_id=%s",
                    job_id
                )
                return

            if job.job_state.is_terminal():
                logger.info(
                    "Job already in terminal state: job_id=%s, state=%s",
                    job_id, job.job_state.value
                )
                return

            job.complete()
            job_repo.save(job)

            event = AuditEvent(
                event_id=str(uuid_generator.generate()),
                job_id=job_id,
                event_type="JOB_COMPLETED",
                correlation_id=correlation_id,
                client_id=client_id,
                timestamp=datetime.now(timezone.utc),
                details={
                    "completion_reason": "All stages completed successfully",
                },
            )
            audit_repo.save(event)

            # Commit sessions if repositories have active sessions
            if hasattr(job_repo, 'session') and job_repo.session:
                job_repo.session.commit()
            if hasattr(audit_repo, 'session') and audit_repo.session:
                audit_repo.session.commit()

            logger.info(
                "Job marked as COMPLETED: job_id=%s",
                job_id
            )

        except Exception as exc:
            logger.exception(
                "Failed to update job state on completion: job_id=%s, error=%s",
                job_id, exc
            )
