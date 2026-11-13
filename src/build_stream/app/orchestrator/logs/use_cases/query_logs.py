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

# ****
# Secure code generated utilizing Code Guardian.
# Applicable rules used: CG-AUTH-001.2, CG-INPUT-001.5, CG-LOGGING-001.2, CG-OUTPUT-001.3
# ****

"""LogQueryUseCase: serve redacted stage logs for an owned job (ER-BSM-003 FR-2.1, FR-3.2)."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from api.logging_utils import log_secure_info
from core.jobs.entities.stage import Stage
from core.jobs.exceptions import JobNotFoundError
from core.jobs.repositories import JobRepository, StageRepository
from core.jobs.value_objects import ClientId, JobId, StageState
from core.logs.exceptions import (
    InvalidLogQueryError,
    LogNotAvailableError,
    LogPathViolationError,
    LogUnavailableReason,
    StageNotFoundForJobError,
)
from core.logs.redaction import RedactionService, RedactionTier
from core.logs.services import LogFileService, LogReadResult

ACTIVE_STAGE_STATES = frozenset({StageState.PENDING, StageState.IN_PROGRESS})


@dataclass(frozen=True)
class LogQuerySettings:
    """Bounds applied to every log query."""

    default_tail_lines: int = 50
    max_tail_lines: int = 10000
    max_response_bytes: int = 10 * 1024 * 1024


@dataclass(frozen=True)
class LogQueryCommand:
    """A validated log query request."""

    job_id: JobId
    client_id: ClientId
    correlation_id: str
    stage: Optional[str] = None
    tail_lines: Optional[int] = None
    full: bool = False


@dataclass(frozen=True)
class StageLogResult:  # pylint: disable=too-many-instance-attributes
    """Log content (or the reason it is unavailable) for one stage."""

    stage_name: str
    stage_state: str
    has_log: bool
    log_content: Optional[str]
    total_lines: int
    returned_lines: int
    truncated: bool
    unavailable_reason: Optional[str] = None


@dataclass(frozen=True)
class LogQueryResult:
    """Log query outcome for a job."""

    job_id: str
    tail_lines: Optional[int]
    full: bool
    stages: List[StageLogResult]


class LogQueryUseCase:  # pylint: disable=too-few-public-methods
    """Resolve, read, and redact stage logs for a job owned by the caller."""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        job_repo: JobRepository,
        stage_repo: StageRepository,
        log_files: LogFileService,
        redaction: RedactionService,
        settings: LogQuerySettings,
    ) -> None:
        """Inject repositories, the log reader, redaction, and query bounds."""
        self._job_repo = job_repo
        self._stage_repo = stage_repo
        self._log_files = log_files
        self._redaction = redaction
        self._settings = settings

    def execute(self, command: LogQueryCommand) -> LogQueryResult:
        """Run the query.

        Raises:
            InvalidLogQueryError: Parameters are out of range or conflicting.
            JobNotFoundError: Job is missing, tombstoned, or owned by another client.
            StageNotFoundForJobError: The requested stage does not exist for the job.
            LogNotAvailableError: A single requested stage has no servable log.
            LogPathViolationError: A stored path escapes the log root.
        """
        tail_lines = self._effective_tail_lines(command)
        job = self._job_repo.find_by_id(command.job_id)
        if job is None or job.tombstoned or job.client_id != command.client_id:
            raise JobNotFoundError(str(command.job_id), command.correlation_id)

        stages = self._stage_repo.find_all_by_job(command.job_id)
        if command.stage is not None:
            stages = [s for s in stages if str(s.stage_name) == command.stage]
            if not stages:
                raise StageNotFoundForJobError()

        results = [self._read_stage(command, stage, tail_lines) for stage in stages]
        if command.stage is not None and not results[0].has_log:
            raise LogNotAvailableError(LogUnavailableReason(results[0].unavailable_reason))
        return LogQueryResult(
            job_id=str(command.job_id),
            tail_lines=None if command.full else tail_lines,
            full=command.full,
            stages=results,
        )

    def _effective_tail_lines(self, command: LogQueryCommand) -> int:
        """Validate parameters and return the number of tail lines to serve."""
        if command.full and command.tail_lines is not None:
            raise InvalidLogQueryError(
                "INVALID_PARAMETERS", "full and tail_lines are mutually exclusive"
            )
        if command.tail_lines is None:
            return self._settings.default_tail_lines
        if not 1 <= command.tail_lines <= self._settings.max_tail_lines:
            raise InvalidLogQueryError(
                "INVALID_TAIL_LINES",
                f"tail_lines must be between 1 and {self._settings.max_tail_lines}",
            )
        return command.tail_lines

    def _read_stage(
        self, command: LogQueryCommand, stage: Stage, tail_lines: int
    ) -> StageLogResult:
        """Read and redact one stage log, or describe why it is unavailable."""
        job_id = str(command.job_id)
        try:
            if not stage.log_file_path:
                reason = (
                    LogUnavailableReason.NOT_YET_AVAILABLE
                    if stage.stage_state in ACTIVE_STAGE_STATES
                    else LogUnavailableReason.NOT_RECORDED
                )
                raise LogNotAvailableError(reason)
            path = self._log_files.resolve(stage.log_file_path, job_id)
            read = self._read(path, command.full, tail_lines)
        except LogPathViolationError:
            log_secure_info(
                "warning",
                f"Security event: log path violation for stage={stage.stage_name}; "
                f"stored path rejected, correlation_id={command.correlation_id}",
                identifier=command.client_id.value,
                job_id=job_id,
            )
            raise
        except LogNotAvailableError as exc:
            return _unavailable(stage, exc.reason)
        except OSError:
            return _unavailable(stage, LogUnavailableReason.MISSING)

        redacted = self._redaction.redact_lines(read.lines, RedactionTier.SECRETS_ONLY)
        if redacted.redacted_lines:
            log_secure_info(
                "info",
                f"Response-time redaction applied: stage={stage.stage_name}, "
                f"lines_redacted={redacted.redacted_lines}",
                job_id=job_id,
            )
        if redacted.suppressed_lines:
            log_secure_info(
                "warning",
                f"Security event: redaction failed, lines withheld: stage={stage.stage_name}, "
                f"lines_suppressed={redacted.suppressed_lines}",
                job_id=job_id,
            )
        return StageLogResult(
            stage_name=str(stage.stage_name),
            stage_state=stage.stage_state.value,
            has_log=True,
            log_content="\n".join(redacted.lines),
            total_lines=read.total_lines,
            returned_lines=len(redacted.lines),
            truncated=read.truncated,
        )

    def _read(self, path: Path, full: bool, tail_lines: int) -> LogReadResult:
        """Read either the bounded full log or its tail."""
        if full:
            return self._log_files.read_full(path, self._settings.max_response_bytes)
        return self._log_files.read_tail(path, tail_lines, self._settings.max_response_bytes)


def _unavailable(stage: Stage, reason: LogUnavailableReason) -> StageLogResult:
    """Build a result entry for a stage whose log cannot be served."""
    return StageLogResult(
        stage_name=str(stage.stage_name),
        stage_state=stage.stage_state.value,
        has_log=False,
        log_content=None,
        total_lines=0,
        returned_lines=0,
        truncated=False,
        unavailable_reason=reason.value,
    )
