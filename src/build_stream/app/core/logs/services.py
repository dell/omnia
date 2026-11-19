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
# Applicable rules used: CG-INPUT-001.5
# ****

"""Port for reading published stage logs."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Protocol


@dataclass(frozen=True)
class LogReadResult:
    """A window of log lines read from one stage log.

    Attributes:
        lines: Decoded lines (without trailing newline characters).
        total_lines: Number of lines in the whole file at read time.
        truncated: True when ``lines`` is not the entire log.
    """

    lines: List[str]
    total_lines: int
    truncated: bool


class LogFileService(Protocol):
    """Resolves and reads stage log files below the configured log root."""

    def resolve(self, stored_path: str, job_id: str) -> Path:
        """Translate a stored host log path to a readable path under the log root.

        Raises:
            LogNotAvailableError: The log is not published or no longer exists.
            LogPathViolationError: The stored path escapes the log root.
        """

    def read_tail(self, path: Path, lines: int, max_bytes: int) -> LogReadResult:
        """Return the last ``lines`` lines, bounded by ``max_bytes``.

        Raises:
            LogContentError: The file contains binary content.
        """

    def read_full(self, path: Path, max_bytes: int) -> LogReadResult:
        """Return the whole log, keeping only the last ``max_bytes`` bytes.

        Raises:
            LogContentError: The file contains binary content.
        """

    def count_lines(self, path: Path) -> int:
        """Return the number of lines in the log."""
