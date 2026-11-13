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
# Applicable rules used: CG-OUTPUT-001.2
# ****

"""Domain exceptions for pipeline log queries.

Messages are client-safe: they never contain file-system paths or log content.
"""

from enum import Enum


class LogUnavailableReason(str, Enum):
    """Why a stage log cannot be served."""

    NOT_YET_AVAILABLE = "NOT_YET_AVAILABLE"
    NOT_RECORDED = "NOT_RECORDED"
    NOT_PUBLISHED = "NOT_PUBLISHED"
    MISSING = "MISSING"
    NOT_TEXT = "NOT_TEXT"


UNAVAILABLE_MESSAGES = {
    LogUnavailableReason.NOT_YET_AVAILABLE: "Stage log not yet available",
    LogUnavailableReason.NOT_RECORDED: "Log file not available for this stage",
    LogUnavailableReason.NOT_PUBLISHED: "Log file not available for this stage",
    LogUnavailableReason.MISSING: "Log file not available for this stage",
    LogUnavailableReason.NOT_TEXT: "Stage log is not readable text",
}


class LogQueryError(Exception):
    """Base class for log query errors."""

    def __init__(self, message: str) -> None:
        """Store a client-safe message."""
        super().__init__(message)
        self.message = message


class InvalidLogQueryError(LogQueryError):
    """Query parameters are invalid."""

    def __init__(self, error_code: str, message: str) -> None:
        """Store the stable error code with the message."""
        super().__init__(message)
        self.error_code = error_code


class StageNotFoundForJobError(LogQueryError):
    """The requested stage does not exist for the job."""

    def __init__(self) -> None:
        """Use the contract message from ER-BSM-003 FR-2.1."""
        super().__init__("Stage not found for job")


class LogNotAvailableError(LogQueryError):
    """The stage log cannot be served (not produced, not published, or removed)."""

    def __init__(self, reason: LogUnavailableReason) -> None:
        """Map the reason to its client-safe message."""
        super().__init__(UNAVAILABLE_MESSAGES[reason])
        self.reason = reason


class LogContentError(LogNotAvailableError):
    """The stage log contains binary content and is not served."""

    def __init__(self) -> None:
        """Report the log as non-text."""
        super().__init__(LogUnavailableReason.NOT_TEXT)


class LogPathViolationError(LogQueryError):
    """A stored log path resolves outside the configured log root."""

    def __init__(self) -> None:
        """Use a generic message that does not echo the offending path."""
        super().__init__("Log path violation")
