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

"""TC-UT-001 / TC-UT-002: LogQueryUseCase tail semantics and ownership (ER-BSM-003 FR-2.1)."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.jobs.entities.stage import Stage
from core.jobs.exceptions import JobNotFoundError
from core.jobs.value_objects import ClientId, JobId, StageName, StageState
from core.logs.exceptions import (
    InvalidLogQueryError,
    LogContentError,
    LogNotAvailableError,
    LogPathViolationError,
    LogUnavailableReason,
    StageNotFoundForJobError,
)
from core.logs.redaction import RedactionService
from core.logs.redaction_patterns import REDACTED
from core.logs.services import LogReadResult
from orchestrator.logs.use_cases import LogQueryCommand, LogQuerySettings, LogQueryUseCase

pytestmark = pytest.mark.unit

JOB_ID = JobId("019bf590-1234-7890-abcd-ef1234567890")
CLIENT_A = ClientId("client-A")
CLIENT_B = ClientId("client-B")
RESOLVED = Path("/opt/omnia/build_stream/log/job/stage.log")


def _stage(name: str, state: StageState, log_path=None) -> Stage:
    """Build a stage entity."""
    return Stage(
        job_id=JOB_ID,
        stage_name=StageName(name),
        stage_state=state,
        log_file_path=log_path,
    )


def _host(name: str) -> str:
    """Host log path for a stage file."""
    return f"/mnt/share/build_stream/log/{JOB_ID}/{name}.log"


@pytest.fixture(name="stages")
def stages_fixture():
    """Three stages: two with published logs, one still running."""
    return [
        _stage("parse-catalog", StageState.COMPLETED, _host("parse")),
        _stage("build-image", StageState.COMPLETED, _host("build")),
        _stage("deploy", StageState.IN_PROGRESS),
    ]


@pytest.fixture(name="log_files")
def log_files_fixture():
    """Mocked LogFileService returning a fixed window."""
    files = MagicMock()
    files.resolve.return_value = RESOLVED
    files.read_tail.return_value = LogReadResult(
        lines=["ok", "password=hunter2"], total_lines=500, truncated=True
    )
    files.read_full.return_value = LogReadResult(
        lines=["a", "b"], total_lines=2, truncated=False
    )
    return files


@pytest.fixture(name="use_case")
def use_case_fixture(stages, log_files):
    """Use case owned by client A with mocked repositories."""
    job_repo = MagicMock()
    job_repo.find_by_id.return_value = SimpleNamespace(client_id=CLIENT_A, tombstoned=False)
    stage_repo = MagicMock()
    stage_repo.find_all_by_job.return_value = stages
    return LogQueryUseCase(
        job_repo=job_repo,
        stage_repo=stage_repo,
        log_files=log_files,
        redaction=RedactionService(),
        settings=LogQuerySettings(default_tail_lines=50, max_tail_lines=10000),
    )


def _cmd(**kwargs) -> LogQueryCommand:
    """Command for client A with overrides."""
    base = {"job_id": JOB_ID, "client_id": CLIENT_A, "correlation_id": "corr-1"}
    base.update(kwargs)
    return LogQueryCommand(**base)


class TestTailSemantics:
    """TC-UT-001."""

    def test_omitted_tail_lines_applies_default(self, use_case, log_files):
        """GIVEN tail_lines omitted WHEN executed THEN read_tail uses the default of 50."""
        result = use_case.execute(_cmd())
        log_files.read_tail.assert_called_with(RESOLVED, 50, 10 * 1024 * 1024)
        assert result.tail_lines == 50

    def test_explicit_tail_lines_override(self, use_case, log_files):
        """GIVEN tail_lines=100 WHEN executed THEN read_tail uses 100."""
        use_case.execute(_cmd(tail_lines=100))
        log_files.read_tail.assert_called_with(RESOLVED, 100, 10 * 1024 * 1024)

    def test_full_reads_bounded_complete_log(self, use_case, log_files):
        """GIVEN full=True WHEN executed THEN read_full is bounded by max_response_bytes."""
        result = use_case.execute(_cmd(full=True))
        log_files.read_full.assert_called_with(RESOLVED, 10485760)
        assert result.full is True
        assert result.tail_lines is None
        assert result.stages[0].truncated is False

    def test_full_and_tail_lines_mutually_exclusive(self, use_case):
        """GIVEN full=True and tail_lines WHEN executed THEN a validation error is raised."""
        with pytest.raises(InvalidLogQueryError) as exc:
            use_case.execute(_cmd(full=True, tail_lines=50))
        assert exc.value.error_code == "INVALID_PARAMETERS"

    @pytest.mark.parametrize("tail_lines", [0, -1, 10001])
    def test_tail_lines_out_of_range(self, use_case, tail_lines):
        """GIVEN tail_lines outside 1..10000 THEN the contract message is returned."""
        with pytest.raises(InvalidLogQueryError) as exc:
            use_case.execute(_cmd(tail_lines=tail_lines))
        assert exc.value.message == "tail_lines must be between 1 and 10000"

    def test_all_stages_returned_with_running_stage_unavailable(self, use_case):
        """All stages are listed; the running stage reports NOT_YET_AVAILABLE."""
        result = use_case.execute(_cmd())
        by_name = {s.stage_name: s for s in result.stages}
        assert set(by_name) == {"parse-catalog", "build-image", "deploy"}
        assert by_name["build-image"].has_log is True
        assert by_name["build-image"].total_lines == 500
        assert by_name["deploy"].has_log is False
        assert by_name["deploy"].unavailable_reason == "NOT_YET_AVAILABLE"

    def test_response_content_is_redacted(self, use_case):
        """Response-time redaction removes secrets from served lines (FR-3.2)."""
        result = use_case.execute(_cmd(stage="build-image"))
        content = result.stages[0].log_content
        assert "hunter2" not in content
        assert REDACTED in content


class TestOwnership:
    """TC-UT-002."""

    def test_non_owned_job_raises_not_found(self, use_case):
        """GIVEN a job owned by client B WHEN client A queries THEN JobNotFoundError."""
        use_case._job_repo.find_by_id.return_value = SimpleNamespace(  # pylint: disable=protected-access
            client_id=CLIENT_B, tombstoned=False
        )
        with pytest.raises(JobNotFoundError):
            use_case.execute(_cmd())

    def test_owned_job_returns_content(self, use_case):
        """GIVEN a job owned by client A WHEN client A queries THEN content is returned."""
        assert use_case.execute(_cmd()).stages[0].log_content is not None

    @pytest.mark.parametrize("job", [None, SimpleNamespace(client_id=CLIENT_A, tombstoned=True)])
    def test_missing_or_tombstoned_job(self, use_case, job):
        """Missing and tombstoned jobs are both not found."""
        use_case._job_repo.find_by_id.return_value = job  # pylint: disable=protected-access
        with pytest.raises(JobNotFoundError):
            use_case.execute(_cmd())


class TestStageFilterAndErrors:
    """Single-stage queries and error propagation."""

    def test_unknown_stage_raises(self, use_case):
        """GIVEN a stage the job does not have THEN StageNotFoundForJobError."""
        with pytest.raises(StageNotFoundForJobError):
            use_case.execute(_cmd(stage="nonexistent-stage"))

    def test_single_running_stage_not_available(self, use_case):
        """GIVEN a single running stage THEN LogNotAvailableError(NOT_YET_AVAILABLE)."""
        with pytest.raises(LogNotAvailableError) as exc:
            use_case.execute(_cmd(stage="deploy"))
        assert exc.value.reason == LogUnavailableReason.NOT_YET_AVAILABLE

    def test_legacy_completed_stage_without_path(self, use_case, stages):
        """GIVEN a completed legacy stage with no log path THEN NOT_RECORDED."""
        stages[1].log_file_path = None
        with pytest.raises(LogNotAvailableError) as exc:
            use_case.execute(_cmd(stage="build-image"))
        assert exc.value.reason == LogUnavailableReason.NOT_RECORDED

    def test_binary_single_stage(self, use_case, log_files):
        """GIVEN binary content THEN the NOT_TEXT reason is propagated."""
        log_files.read_tail.side_effect = LogContentError()
        with pytest.raises(LogNotAvailableError) as exc:
            use_case.execute(_cmd(stage="build-image"))
        assert exc.value.reason == LogUnavailableReason.NOT_TEXT

    def test_missing_file_in_multi_stage_query(self, use_case, log_files):
        """A vanished file is reported per stage, not as a request failure."""
        log_files.read_tail.side_effect = OSError("gone")
        result = use_case.execute(_cmd())
        assert result.stages[0].unavailable_reason == "MISSING"

    def test_path_violation_fails_request_and_logs_security_event(self, use_case, log_files):
        """GIVEN a stored path escaping the root THEN the whole request fails closed."""
        log_files.resolve.side_effect = LogPathViolationError()
        with patch("orchestrator.logs.use_cases.query_logs.log_secure_info") as log:
            with pytest.raises(LogPathViolationError):
                use_case.execute(_cmd())
        assert "Security event" in log.call_args.args[1]

    def test_suppressed_lines_logged_as_security_event(self, use_case):
        """Redaction failures are logged without their content."""
        use_case._redaction = MagicMock()  # pylint: disable=protected-access
        use_case._redaction.redact_lines.return_value = SimpleNamespace(  # pylint: disable=protected-access
            lines=["[REDACTION ERROR]"], redacted_lines=0, suppressed_lines=1
        )
        with patch("orchestrator.logs.use_cases.query_logs.log_secure_info") as log:
            use_case.execute(_cmd(stage="build-image"))
        messages = [c.args[1] for c in log.call_args_list]
        assert any("lines_suppressed=1" in m for m in messages)
