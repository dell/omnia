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

"""Job aggregate root entity."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ..exceptions import InvalidStateTransitionError, TerminalStateViolationError
from ..value_objects import ClientId, JobId, JobState


@dataclass
class Job:
    """Job aggregate root.

    Represents a build workflow execution with lifecycle management,
    state tracking, and optimistic locking.

    Attributes:
        job_id: Unique job identifier.
        client_id: Client who owns this job (from auth).
        request_client_id: Client ID from request payload.
        job_state: Current lifecycle state.
        client_name: Optional client name.
        created_at: Job creation timestamp.
        updated_at: Last modification timestamp.
        version: Optimistic locking version.
        tombstoned: Soft delete flag.
    """

    job_id: JobId
    client_id: ClientId
    request_client_id: str
    client_name: Optional[str] = None
    job_state: JobState = JobState.CREATED
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    tombstoned: bool = False

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = self.created_at

    def _validate_transition(
        self,
        allowed_states: set[JobState],
        target_state: JobState
    ) -> None:
        """Validate state transition is allowed.

        Args:
            allowed_states: States from which transition is valid.
            target_state: Desired target state.

        Raises:
            TerminalStateViolationError: If in terminal state.
            InvalidStateTransitionError: If transition invalid.
        """
        if self.job_state.is_terminal():
            raise TerminalStateViolationError(
                entity_type="Job",
                entity_id=str(self.job_id),
                state=self.job_state.value
            )

        if self.job_state not in allowed_states:
            raise InvalidStateTransitionError(
                entity_type="Job",
                entity_id=str(self.job_id),
                from_state=self.job_state.value,
                to_state=target_state.value
            )

    def _update_metadata(self) -> None:
        """Update timestamp and version after state change."""
        self.updated_at = datetime.now(timezone.utc)
        self.version += 1

    def start(self) -> None:
        """Transition job from CREATED to IN_PROGRESS.

        Raises:
            InvalidStateTransitionError: If not in CREATED state.
            TerminalStateViolationError: If in terminal state.
        """
        self._validate_transition({JobState.CREATED}, JobState.IN_PROGRESS)
        self.job_state = JobState.IN_PROGRESS
        self._update_metadata()

    def complete(self) -> None:
        """Transition job to COMPLETED state.

        Raises:
            InvalidStateTransitionError: If not in IN_PROGRESS state.
            TerminalStateViolationError: If already in terminal state.
        """
        self._validate_transition({JobState.IN_PROGRESS}, JobState.COMPLETED)
        self.job_state = JobState.COMPLETED
        self._update_metadata()

    def fail(self) -> None:
        """Transition job to FAILED state.

        Raises:
            InvalidStateTransitionError: If not in IN_PROGRESS state.
            TerminalStateViolationError: If already in terminal state.
        """
        self._validate_transition({JobState.IN_PROGRESS}, JobState.FAILED)
        self.job_state = JobState.FAILED
        self._update_metadata()

    def cancel(self) -> None:
        """Transition job to CANCELLED state.

        Can be called from CREATED or IN_PROGRESS states.

        Raises:
            InvalidStateTransitionError: If not in valid state for cancellation.
            TerminalStateViolationError: If already in terminal state.
        """
        self._validate_transition(
            {JobState.CREATED, JobState.IN_PROGRESS},
            JobState.CANCELLED
        )
        self.job_state = JobState.CANCELLED
        self._update_metadata()

    def tombstone(self) -> None:
        """Mark job as tombstoned (soft delete).

        Tombstoned jobs cannot be modified but remain queryable.
        """
        self.tombstoned = True
        self._update_metadata()

    def is_completed(self) -> bool:
        """Check if job is in COMPLETED state."""
        return self.job_state == JobState.COMPLETED

    def is_failed(self) -> bool:
        """Check if job is in FAILED state."""
        return self.job_state == JobState.FAILED

    def is_cancelled(self) -> bool:
        """Check if job is in CANCELLED state."""
        return self.job_state == JobState.CANCELLED

    def is_in_progress(self) -> bool:
        """Check if job is in IN_PROGRESS state."""
        return self.job_state == JobState.IN_PROGRESS
