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

"""Unit tests for Stage entity."""

import pytest

from build_stream.core.jobs.entities.stage import Stage
from build_stream.core.jobs.exceptions import (
    InvalidStateTransitionError,
    TerminalStateViolationError,
)
from build_stream.core.jobs.value_objects import JobId, StageName, StageState


class TestStage:
    """Tests for Stage entity."""

    def test_create_stage(self):
        """Stage should be created with initial state."""
        stage = Stage(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            stage_name=StageName("parse-catalog"),
        )
        assert stage.stage_state == StageState.PENDING
        assert stage.attempt == 1
        assert stage.version == 1
        assert stage.started_at is None
        assert stage.ended_at is None

    def test_start_stage(self):
        """Stage should transition from PENDING to IN_PROGRESS."""
        stage = Stage(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            stage_name=StageName("parse-catalog"),
        )
        stage.start()
        assert stage.stage_state == StageState.IN_PROGRESS
        assert stage.started_at is not None
        assert stage.version == 2

    def test_start_stage_invalid_state(self):
        """Starting stage from non-PENDING state should fail."""
        stage = Stage(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            stage_name=StageName("parse-catalog"),
            stage_state=StageState.IN_PROGRESS,
        )
        with pytest.raises(InvalidStateTransitionError):
            stage.start()

    def test_complete_stage(self):
        """Stage should transition from IN_PROGRESS to COMPLETED."""
        stage = Stage(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            stage_name=StageName("parse-catalog"),
            stage_state=StageState.IN_PROGRESS,
        )
        stage.complete()
        assert stage.stage_state == StageState.COMPLETED
        assert stage.ended_at is not None
        assert stage.version == 2

    def test_fail_stage(self):
        """Stage should transition from IN_PROGRESS to FAILED with error details."""
        stage = Stage(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            stage_name=StageName("parse-catalog"),
            stage_state=StageState.IN_PROGRESS,
        )
        stage.fail(error_code="ERR_PARSE", error_summary="Parse failed")
        assert stage.stage_state == StageState.FAILED
        assert stage.error_code == "ERR_PARSE"
        assert stage.error_summary == "Parse failed"
        assert stage.ended_at is not None
        assert stage.version == 2

    def test_skip_stage(self):
        """Stage should transition from PENDING to SKIPPED."""
        stage = Stage(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            stage_name=StageName("parse-catalog"),
        )
        stage.skip()
        assert stage.stage_state == StageState.SKIPPED
        assert stage.ended_at is not None
        assert stage.version == 2

    def test_cancel_stage_from_pending(self):
        """Stage should be cancellable from PENDING state."""
        stage = Stage(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            stage_name=StageName("parse-catalog"),
        )
        stage.cancel()
        assert stage.stage_state == StageState.CANCELLED
        assert stage.ended_at is not None

    def test_cancel_stage_from_in_progress(self):
        """Stage should be cancellable from IN_PROGRESS state."""
        stage = Stage(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            stage_name=StageName("parse-catalog"),
            stage_state=StageState.IN_PROGRESS,
        )
        stage.cancel()
        assert stage.stage_state == StageState.CANCELLED

    def test_terminal_state_prevents_transitions(self):
        """Terminal states should prevent any transitions."""
        stage = Stage(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            stage_name=StageName("parse-catalog"),
            stage_state=StageState.COMPLETED,
        )
        with pytest.raises(TerminalStateViolationError):
            stage.start()
        with pytest.raises(TerminalStateViolationError):
            stage.complete()
        with pytest.raises(TerminalStateViolationError):
            stage.fail("ERR", "Error")
        with pytest.raises(TerminalStateViolationError):
            stage.skip()
        with pytest.raises(TerminalStateViolationError):
            stage.cancel()
