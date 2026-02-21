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

"""Stage entity within Job aggregate."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ..exceptions import InvalidStateTransitionError, TerminalStateViolationError
from ..value_objects import JobId, StageName, StageState


@dataclass
class Stage:
    """Stage entity within Job aggregate.

    Represents a single stage execution with state tracking,
    error handling, and retry support.

    Attributes:
        job_id: Parent job identifier.
        stage_name: Stage identifier.
        stage_state: Current execution state.
        attempt: Execution attempt number (1-indexed).
        started_at: Stage start timestamp.
        ended_at: Stage end timestamp.
        error_code: Error code if failed.
        error_summary: Error description if failed.
        version: Optimistic locking version.
    """

    job_id: JobId
    stage_name: StageName
    stage_state: StageState = StageState.PENDING
    attempt: int = 1
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_summary: Optional[str] = None
    version: int = 1

    def _initialize_timestamps(self) -> None:
        """Initialize timestamps when not provided (rehydration support)."""
        # Note: Stages don't auto-stamp on creation like Jobs
        # because they start as PENDING and get stamped when actually started/ended
        # No initialization needed for stages

    def _validate_transition(
        self,
        allowed_states: set[StageState],
        target_state: StageState
    ) -> None:
        """Validate state transition is allowed.

        Args:
            allowed_states: States from which transition is valid.
            target_state: Desired target state.

        Raises:
            TerminalStateViolationError: If in terminal state.
            InvalidStateTransitionError: If transition invalid.
        """
        if self.stage_state.is_terminal():
            raise TerminalStateViolationError(
                entity_type="Stage",
                entity_id=f"{self.job_id}/{self.stage_name}",
                state=self.stage_state.value
            )

        if self.stage_state not in allowed_states:
            raise InvalidStateTransitionError(
                entity_type="Stage",
                entity_id=f"{self.job_id}/{self.stage_name}",
                from_state=self.stage_state.value,
                to_state=target_state.value
            )

    def _mark_started(self) -> None:
        """Mark stage as started."""
        self.started_at = datetime.now(timezone.utc)
        self.version += 1

    def _mark_ended(self) -> None:
        """Mark stage as ended."""
        self.ended_at = datetime.now(timezone.utc)
        self.version += 1

    def start(self) -> None:
        """Transition stage from PENDING to IN_PROGRESS.

        Raises:
            InvalidStateTransitionError: If not in PENDING state.
            TerminalStateViolationError: If in terminal state.
        """
        self._validate_transition({StageState.PENDING}, StageState.IN_PROGRESS)
        self.stage_state = StageState.IN_PROGRESS
        self._mark_started()

    def complete(self) -> None:
        """Transition stage to COMPLETED state.

        Raises:
            InvalidStateTransitionError: If not in IN_PROGRESS state.
            TerminalStateViolationError: If already in terminal state.
        """
        self._validate_transition({StageState.IN_PROGRESS}, StageState.COMPLETED)
        self.stage_state = StageState.COMPLETED
        self._mark_ended()

    def fail(self, error_code: str, error_summary: str) -> None:
        """Transition stage to FAILED state with error details.

        Args:
            error_code: Error classification code.
            error_summary: Human-readable error description.

        Raises:
            InvalidStateTransitionError: If not in IN_PROGRESS state.
            TerminalStateViolationError: If already in terminal state.
        """
        self._validate_transition({StageState.IN_PROGRESS}, StageState.FAILED)
        self.stage_state = StageState.FAILED
        self.error_code = error_code
        self.error_summary = error_summary
        self._mark_ended()

    def skip(self) -> None:
        """Transition stage to SKIPPED state.

        Raises:
            InvalidStateTransitionError: If not in PENDING state.
            TerminalStateViolationError: If already in terminal state.
        """
        self._validate_transition({StageState.PENDING}, StageState.SKIPPED)
        self.stage_state = StageState.SKIPPED
        self._mark_ended()

    def cancel(self) -> None:
        """Transition stage to CANCELLED state.

        Can be called from PENDING or IN_PROGRESS states.

        Raises:
            InvalidStateTransitionError: If not in valid state for cancellation.
            TerminalStateViolationError: If already in terminal state.
        """
        self._validate_transition(
            {StageState.PENDING, StageState.IN_PROGRESS},
            StageState.CANCELLED
        )
        self.stage_state = StageState.CANCELLED
        self._mark_ended()
