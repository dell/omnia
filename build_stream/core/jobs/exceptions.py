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

"""Domain exceptions for Job aggregate."""

from typing import Optional


class JobDomainError(Exception):
    """Base exception for all job domain errors."""

    def __init__(self, message: str, correlation_id: Optional[str] = None) -> None:
        """Initialize domain error.

        Args:
            message: Human-readable error description.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(message)
        self.message = message
        self.correlation_id = correlation_id


class JobNotFoundError(JobDomainError):
    """Job does not exist in the system."""

    def __init__(self, job_id: str, correlation_id: Optional[str] = None) -> None:
        """Initialize job not found error.

        Args:
            job_id: The job ID that was not found.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(
            f"Job not found: {job_id}",
            correlation_id=correlation_id
        )
        self.job_id = job_id


class JobAlreadyExistsError(JobDomainError):
    """Job with the given ID already exists."""

    def __init__(self, job_id: str, correlation_id: Optional[str] = None) -> None:
        """Initialize job already exists error.

        Args:
            job_id: The job ID that already exists.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(
            f"Job already exists: {job_id}",
            correlation_id=correlation_id
        )
        self.job_id = job_id


class InvalidStateTransitionError(JobDomainError):
    """Attempted state transition is not valid."""

    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        from_state: str,
        to_state: str,
        correlation_id: Optional[str] = None
    ) -> None:
        """Initialize invalid state transition error.

        Args:
            entity_type: Type of entity (Job or Stage).
            entity_id: Identifier of the entity.
            from_state: Current state.
            to_state: Attempted target state.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(
            f"Invalid {entity_type} state transition for {entity_id}: "
            f"{from_state} -> {to_state}",
            correlation_id=correlation_id
        )
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.from_state = from_state
        self.to_state = to_state


class TerminalStateViolationError(JobDomainError):
    """Attempted to modify an entity in a terminal state."""

    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        state: str,
        correlation_id: Optional[str] = None
    ) -> None:
        """Initialize terminal state violation error.

        Args:
            entity_type: Type of entity (Job or Stage).
            entity_id: Identifier of the entity.
            state: Current terminal state.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(
            f"Cannot modify {entity_type} {entity_id} in terminal state: {state}",
            correlation_id=correlation_id
        )
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.state = state


class OptimisticLockError(JobDomainError):
    """Version conflict detected during update."""

    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        expected_version: int,
        actual_version: int,
        correlation_id: Optional[str] = None
    ) -> None:
        """Initialize optimistic lock error.

        Args:
            entity_type: Type of entity (Job or Stage).
            entity_id: Identifier of the entity.
            expected_version: Version expected by the client.
            actual_version: Current version in the system.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(
            f"Version conflict for {entity_type} {entity_id}: "
            f"expected {expected_version}, found {actual_version}",
            correlation_id=correlation_id
        )
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.expected_version = expected_version
        self.actual_version = actual_version


class IdempotencyConflictError(JobDomainError):
    """Idempotency key conflict with different request fingerprint."""

    def __init__(
        self,
        idempotency_key: str,
        existing_job_id: str,
        correlation_id: Optional[str] = None
    ) -> None:
        """Initialize idempotency conflict error.

        Args:
            idempotency_key: The conflicting idempotency key.
            existing_job_id: Job ID associated with the key.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(
            f"Idempotency key {idempotency_key} already used for job {existing_job_id} "
            f"with different request fingerprint",
            correlation_id=correlation_id
        )
        self.idempotency_key = idempotency_key
        self.existing_job_id = existing_job_id


class StageAlreadyCompletedError(JobDomainError):
    """Stage has already been completed for this job."""

    def __init__(
        self,
        job_id: str,
        stage_name: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Initialize stage already completed error.

        Args:
            job_id: The job ID.
            stage_name: The stage that is already completed.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(
            f"Stage {stage_name} already completed for job {job_id}",
            correlation_id=correlation_id,
        )
        self.job_id = job_id
        self.stage_name = stage_name


class UpstreamStageNotCompletedError(JobDomainError):
    """Required upstream stage has not completed."""

    def __init__(
        self,
        job_id: str,
        required_stage: str,
        actual_state: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Initialize upstream stage not completed error.

        Args:
            job_id: The job ID.
            required_stage: The upstream stage that must be completed.
            actual_state: The actual state of the upstream stage.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(
            f"Upstream stage '{required_stage}' must be COMPLETED "
            f"(current state: {actual_state}) for job '{job_id}'",
            correlation_id=correlation_id,
        )
        self.job_id = job_id
        self.required_stage = required_stage
        self.actual_state = actual_state


class StageNotFoundError(JobDomainError):
    """Stage does not exist for the given job."""

    def __init__(
        self,
        job_id: str,
        stage_name: str,
        correlation_id: Optional[str] = None
    ) -> None:
        """Initialize stage not found error.

        Args:
            job_id: The job ID.
            stage_name: The stage name that was not found.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(
            f"Stage {stage_name} not found for job {job_id}",
            correlation_id=correlation_id
        )
        self.job_id = job_id
        self.stage_name = stage_name
