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

"""Value objects for ImageGroup domain.

All value objects are immutable and defined by their values, not identity.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Pattern


@dataclass(frozen=True)
class ImageGroupId:
    """ImageGroup identifier from catalog.

    Unlike JobId (UUID), this is a human-readable string from the catalog
    payload (e.g., 'omnia-cluster-v1.2').

    The constructor checks length only, so rows already stored in the
    database always load. Use :meth:`parse` for values from outside the
    service (uploaded catalogs, API requests); it also enforces the
    allowed character set, which matches the playbook watcher's check.

    Attributes:
        value: ImageGroup identifier string (1-128 characters).

    Raises:
        ValueError: If value is empty or exceeds length.
    """

    value: str

    MIN_LENGTH: ClassVar[int] = 1
    MAX_LENGTH: ClassVar[int] = 128
    FORMAT_PATTERN: ClassVar[Pattern[str]] = re.compile(
        r"[A-Za-z0-9][A-Za-z0-9._-]*"
    )

    def __post_init__(self) -> None:
        """Validate identifier length."""
        if not self.value or not self.value.strip():
            raise ValueError("ImageGroupId cannot be empty")
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"ImageGroupId length cannot exceed {self.MAX_LENGTH} "
                f"characters, got {len(self.value)}"
            )

    @classmethod
    def parse(cls, value: str) -> "ImageGroupId":
        """Build an ImageGroupId from an untrusted value.

        Accepts only letters, digits, '.', '_' and '-', starting with a
        letter or digit. Shell metacharacters, whitespace and path
        separators are rejected before the value is stored or queued.

        Raises:
            ValueError: If the value is not a string, is empty or too long,
                or contains characters outside the allowed set.
        """
        if not isinstance(value, str):
            raise ValueError("ImageGroupId must be a string")
        image_group_id = cls(value)
        if not cls.FORMAT_PATTERN.fullmatch(value):
            raise ValueError(
                "ImageGroupId must start with a letter or digit and contain "
                "only letters, digits, '.', '_' and '-'"
            )
        return image_group_id

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


class ImageGroupStatus(str, Enum):
    """ImageGroup lifecycle states.

    State machine for image group lifecycle through build and deploy pipelines.
    Terminal states: PASSED, FAILED, CLEANED, CLEANUP_FAILED.
    """

    BUILT = "BUILT"
    DEPLOYING = "DEPLOYING"
    DEPLOYED = "DEPLOYED"
    RESTARTING = "RESTARTING"
    RESTARTED = "RESTARTED"
    VALIDATING = "VALIDATING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    CLEANING = "CLEANING"
    CLEANED = "CLEANED"
    CLEANUP_FAILED = "CLEANUP_FAILED"

    def is_terminal(self) -> bool:
        """Check if status is terminal (no further transitions).

        Returns:
            True if status is PASSED, FAILED, CLEANED, or CLEANUP_FAILED.
        """
        return self in {
            ImageGroupStatus.PASSED,
            ImageGroupStatus.FAILED,
            ImageGroupStatus.CLEANED,
            ImageGroupStatus.CLEANUP_FAILED,
        }


class PipelinePhase(str, Enum):
    """Pipeline execution context.

    Optional — NULL/None indicates direct invocation (context-agnostic).
    """

    BUILD = "BUILD"
    DEPLOY = "DEPLOY"
