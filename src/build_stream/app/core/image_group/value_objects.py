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

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar


@dataclass(frozen=True)
class ImageGroupId:
    """ImageGroup identifier from catalog.

    Unlike JobId (UUID), this is a human-readable string from the catalog
    payload (e.g., 'omnia-cluster-v1.2').

    Attributes:
        value: ImageGroup identifier string (1-128 characters).

    Raises:
        ValueError: If value is empty or exceeds length.
    """

    value: str

    MIN_LENGTH: ClassVar[int] = 1
    MAX_LENGTH: ClassVar[int] = 128

    def __post_init__(self) -> None:
        """Validate identifier format and length."""
        if not self.value or not self.value.strip():
            raise ValueError("ImageGroupId cannot be empty")
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"ImageGroupId length cannot exceed {self.MAX_LENGTH} "
                f"characters, got {len(self.value)}"
            )

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


class ImageGroupStatus(str, Enum):
    """ImageGroup lifecycle states.

    State machine for image group lifecycle through build and deploy pipelines.
    Terminal states: PASSED, FAILED, CLEANED.
    """

    BUILT = "BUILT"
    DEPLOYING = "DEPLOYING"
    DEPLOYED = "DEPLOYED"
    RESTARTING = "RESTARTING"
    RESTARTED = "RESTARTED"
    VALIDATING = "VALIDATING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    CLEANED = "CLEANED"

    def is_terminal(self) -> bool:
        """Check if status is terminal (no further transitions).

        Returns:
            True if status is PASSED, FAILED, or CLEANED.
        """
        return self in {
            ImageGroupStatus.PASSED,
            ImageGroupStatus.FAILED,
            ImageGroupStatus.CLEANED,
        }


class PipelinePhase(str, Enum):
    """Pipeline execution context.

    Optional — NULL/None indicates direct invocation (context-agnostic).
    """

    BUILD = "BUILD"
    DEPLOY = "DEPLOY"
