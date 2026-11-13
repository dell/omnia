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
# Applicable rules used: CG-INPUT-001.5, CG-OUTPUT-001.3
# ****

"""StageLogMetadataService: has_log / log_lines for GET /jobs/{id} (ER-BSM-003 FR-2.2)."""

from dataclasses import dataclass

from api.logging_utils import log_secure_info
from core.jobs.entities.stage import Stage
from core.jobs.value_objects import StageState
from core.logs.exceptions import LogNotAvailableError, LogPathViolationError
from core.logs.services import LogFileService

NO_LOG_STATES = frozenset({StageState.PENDING, StageState.IN_PROGRESS})


@dataclass(frozen=True)
class StageLogMetadata:
    """Log availability for one stage."""

    has_log: bool
    log_lines: int


NO_LOG = StageLogMetadata(has_log=False, log_lines=0)


class StageLogMetadataService:  # pylint: disable=too-few-public-methods
    """Describe whether a stage has a servable log and how long it is.

    Never raises: the job detail endpoint must not fail because a log is missing.
    """

    def __init__(self, log_files: LogFileService) -> None:
        """Inject the log reader."""
        self._log_files = log_files

    def describe(self, job_id: str, stage: Stage) -> StageLogMetadata:
        """Return log metadata for a stage of ``job_id``."""
        if not stage.log_file_path or stage.stage_state in NO_LOG_STATES:
            return NO_LOG
        try:
            path = self._log_files.resolve(stage.log_file_path, job_id)
            return StageLogMetadata(has_log=True, log_lines=self._log_files.count_lines(path))
        except LogPathViolationError:
            log_secure_info(
                "warning",
                f"Security event: log path violation for stage={stage.stage_name}; "
                "log metadata withheld",
                job_id=job_id,
            )
        except (LogNotAvailableError, OSError):
            pass
        return NO_LOG
