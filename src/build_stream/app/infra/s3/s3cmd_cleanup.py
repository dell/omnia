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

"""S3 cleanup implementation using the ``s3cmd`` CLI tool.

Executes ``s3cmd del --recursive --force <image_path>`` as a synchronous
subprocess from inside the BuildStream container. Image paths are read
verbatim from the ``images.image_name`` column (which stores the
complete S3 prefix written at build-image completion time).

Security:
    The `image_path` is validated to start with a configured S3 bucket
    URI prefix (default: ``s3://boot-images/``). Subprocesses are
    invoked with a list of arguments (no shell) to avoid command
    injection.
"""

import os
import re
import shlex
import subprocess
from typing import Optional

from api.logging_utils import log_secure_info
from core.cleanup.exceptions import CleanupS3FailedError
from core.cleanup.s3_service import S3CleanupResult, S3CleanupService

DEFAULT_S3_BUCKET_URI = "s3://boot-images"
DEFAULT_S3CMD_BINARY = "s3cmd"
DEFAULT_S3CMD_TIMEOUT_SECONDS = 300

# Allow only a safe subset of characters in S3 paths to defend against
# command injection or path-traversal style attacks. The build-image
# pattern produces alphanumerics, dot, dash, underscore and forward
# slash separators only.
_SAFE_S3_PATH_PATTERN = re.compile(r"^s3://[a-zA-Z0-9._\-/]+/?$")


class S3CmdCleanupService(S3CleanupService):
    """S3 cleanup adapter that shells out to ``s3cmd``."""

    def __init__(
        self,
        bucket_uri: Optional[str] = None,
        s3cmd_binary: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> None:
        """Initialise the service with configuration overrides.

        Args:
            bucket_uri: Allowed S3 bucket URI prefix
                (default: ``s3://boot-images``, configurable via the
                ``CLEANUP_S3_BUCKET`` environment variable).
            s3cmd_binary: Path to the s3cmd executable (default:
                ``s3cmd`` on PATH).
            timeout_seconds: Subprocess timeout in seconds (default:
                300, configurable via ``CLEANUP_S3CMD_TIMEOUT_SECONDS``).
        """
        self._bucket_uri = (
            bucket_uri
            or os.environ.get("CLEANUP_S3_BUCKET", DEFAULT_S3_BUCKET_URI)
        ).rstrip("/")
        self._s3cmd_binary = s3cmd_binary or os.environ.get(
            "CLEANUP_S3CMD_BINARY", DEFAULT_S3CMD_BINARY
        )
        try:
            self._timeout_seconds = int(
                timeout_seconds
                if timeout_seconds is not None
                else os.environ.get(
                    "CLEANUP_S3CMD_TIMEOUT_SECONDS",
                    DEFAULT_S3CMD_TIMEOUT_SECONDS,
                )
            )
        except (TypeError, ValueError):
            self._timeout_seconds = DEFAULT_S3CMD_TIMEOUT_SECONDS

    def delete_image_path(self, image_path: str) -> S3CleanupResult:
        """Delete all objects under the given S3 path via ``s3cmd del``."""
        sanitized = self._validate_path(image_path)

        cmd = [
            self._s3cmd_binary,
            "del",
            "--recursive",
            "--force",
            sanitized,
        ]
        log_secure_info(
            "info",
            f"S3 cleanup: executing {' '.join(shlex.quote(c) for c in cmd)}",
        )

        try:
            result = subprocess.run(  # nosec B603 - argv list, no shell
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise CleanupS3FailedError(
                image_group_id=sanitized,
                exit_code=-1,
                stderr=f"s3cmd timed out after {self._timeout_seconds}s",
            ) from exc

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            # If the prefix does not exist any more (already cleaned or
            # never built), treat as success with zero objects deleted.
            if self._is_missing_path_error(stderr):
                log_secure_info(
                    "warning",
                    f"S3 cleanup: path missing for {sanitized}; "
                    f"continuing as no-op",
                )
                return S3CleanupResult(
                    image_path=sanitized,
                    objects_deleted=0,
                    exit_code=0,
                    success=True,
                )
            raise CleanupS3FailedError(
                image_group_id=sanitized,
                exit_code=result.returncode,
                stderr=stderr,
            )

        deleted_count = self._parse_deleted_count(result.stdout or "")
        log_secure_info(
            "info",
            f"S3 cleanup complete: {deleted_count} objects deleted from "
            f"{sanitized}",
        )
        return S3CleanupResult(
            image_path=sanitized,
            objects_deleted=deleted_count,
            exit_code=result.returncode,
            success=True,
        )

    def _validate_path(self, image_path: str) -> str:
        """Validate the S3 path and return a sanitised version."""
        if not isinstance(image_path, str) or not image_path:
            raise CleanupS3FailedError(
                image_group_id="<empty>",
                exit_code=-1,
                stderr="image_path is empty or invalid",
            )

        candidate = image_path.strip()

        if not candidate.startswith(self._bucket_uri + "/"):
            raise CleanupS3FailedError(
                image_group_id=candidate,
                exit_code=-1,
                stderr=(
                    f"image_path '{candidate}' does not start with "
                    f"allowed bucket URI '{self._bucket_uri}/'"
                ),
            )

        if not _SAFE_S3_PATH_PATTERN.match(candidate):
            raise CleanupS3FailedError(
                image_group_id=candidate,
                exit_code=-1,
                stderr=(
                    f"image_path '{candidate}' contains disallowed characters"
                ),
            )
        return candidate

    @staticmethod
    def _parse_deleted_count(stdout: str) -> int:
        """Parse the ``s3cmd del`` stdout to count deleted objects."""
        if not stdout:
            return 0
        # s3cmd prints one ``delete: s3://...`` line per object removed.
        count = sum(
            1
            for line in stdout.splitlines()
            if line.strip().lower().startswith("delete:")
        )
        if count > 0:
            return count
        # Fallback: count any non-empty lines.
        return sum(1 for line in stdout.splitlines() if line.strip())

    @staticmethod
    def _is_missing_path_error(stderr: str) -> bool:
        """Heuristic: detect ``not found`` style errors from s3cmd."""
        if not stderr:
            return False
        lowered = stderr.lower()
        return (
            "nosuchkey" in lowered
            or "not found" in lowered
            or "does not exist" in lowered
        )
