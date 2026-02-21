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

"""Value objects for Job domain.

All value objects are immutable and defined by their values, not identity.
"""

import uuid
import re
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar


@dataclass(frozen=True)
class JobId:
    """UUID identifier for a job.

    Attributes:
        value: String representation of UUID.

    Raises:
        ValueError: If value does not match UUID format or exceeds length.
    """

    value: str

    MAX_LENGTH: ClassVar[int] = 36  # UUID standard length

    def __post_init__(self) -> None:
        """Validate UUID format and length."""
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"JobId length cannot exceed {self.MAX_LENGTH} characters, "
                f"got {len(self.value)}"
            )
        try:
            uuid_obj = uuid.UUID(self.value)
        except Exception as exc:
            raise ValueError(f"Invalid UUID format: {self.value}") from exc
        # normalize representation
        object.__setattr__(self, "value", str(uuid_obj))

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


@dataclass(frozen=True)
class CorrelationId:
    """UUID identifier for request tracing.

    Attributes:
        value: String representation of UUID.

    Raises:
        ValueError: If value does not match UUID format or exceeds length.
    """

    value: str

    MAX_LENGTH: ClassVar[int] = 36  # UUID standard length

    def __post_init__(self) -> None:
        """Validate UUID format and length."""
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"CorrelationId length cannot exceed {self.MAX_LENGTH} characters, "
                f"got {len(self.value)}"
            )
        try:
            uuid_obj = uuid.UUID(self.value)
        except Exception as exc:
            raise ValueError(f"Invalid UUID format: {self.value}") from exc
        object.__setattr__(self, "value", str(uuid_obj))

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


class StageType(str, Enum):
    """Canonical stage types for BuildStreaM workflow.

    All valid stage identifiers in the closed set. Used by StageName VO
    for validation and by domain logic to avoid raw string comparisons.
    """

    PARSE_CATALOG = "parse-catalog"
    GENERATE_INPUT_FILES = "generate-input-files"
    CREATE_LOCAL_REPOSITORY = "create-local-repository"
    UPDATE_LOCAL_REPOSITORY = "update-local-repository"
    CREATE_IMAGE_REPOSITORY = "create-image-repository"
    BUILD_IMAGE_X86_64 = "build-image-x86_64"
    BUILD_IMAGE_AARCH64 = "build-image-aarch64"
    VALIDATE_IMAGE = "validate-image"
    VALIDATE_IMAGE_ON_TEST = "validate-image-on-test"
    PROMOTE = "promote"


@dataclass(frozen=True)
class StageName:
    """Canonical stage identifier.

    Attributes:
        value: Stage name from canonical set.

    Raises:
        ValueError: If value is not in canonical stages set or exceeds length.
    """

    value: str

    MAX_LENGTH: ClassVar[int] = 30

    def __post_init__(self) -> None:
        """Validate stage name is in canonical set and length."""
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"StageName length cannot exceed {self.MAX_LENGTH} characters, "
                f"got {len(self.value)}"
            )
        try:
            StageType(self.value)
        except ValueError as exc:
            raise ValueError(
                f"Invalid stage name: {self.value}. "
                f"Must be one of: {sorted([stage.value for stage in StageType])}"
            ) from exc

    def as_enum(self) -> StageType:
        """Convert stage name to StageType enum.
        
        Returns:
            StageType: The corresponding enum value.
        """
        return StageType(self.value)

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


@dataclass(frozen=True)
class IdempotencyKey:
    """Client-provided deduplication token.

    Attributes:
        value: Idempotency key string (1-255 characters).

    Raises:
        ValueError: If value length is invalid.
    """

    value: str

    MIN_LENGTH: ClassVar[int] = 1
    MAX_LENGTH: ClassVar[int] = 255

    def __post_init__(self) -> None:
        """Validate key length."""
        length = len(self.value)
        if length < self.MIN_LENGTH or length > self.MAX_LENGTH:
            raise ValueError(
                f"Idempotency key length must be between {self.MIN_LENGTH} "
                f"and {self.MAX_LENGTH} characters, got {length}"
            )

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


@dataclass(frozen=True)
class RequestFingerprint:
    """SHA-256 hash of normalized request payload.

    Attributes:
        value: 64-character hex string (SHA-256 digest).

    Raises:
        ValueError: If value does not match SHA-256 pattern or exceeds length.
    """

    value: str

    SHA256_PATTERN: ClassVar[str] = r'^[0-9a-f]{64}$'
    MAX_LENGTH: ClassVar[int] = 64  # SHA-256 hex digest length

    def __post_init__(self) -> None:
        """Validate SHA-256 format and length."""
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"RequestFingerprint length cannot exceed {self.MAX_LENGTH} characters, "
                f"got {len(self.value)}"
            )
        if not re.match(self.SHA256_PATTERN, self.value.lower()):
            raise ValueError(
                f"Invalid SHA-256 format: {self.value}. "
                f"Expected 64 hexadecimal characters."
            )

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


@dataclass(frozen=True)
class ClientId:
    """Client identity from authentication.

    Attributes:
        value: Client identifier string.

    Raises:
        ValueError: If value is empty or exceeds length.
    """

    value: str

    MAX_LENGTH: ClassVar[int] = 128  # Reasonable client ID length limit

    def __post_init__(self) -> None:
        """Validate client ID is not empty and within length limit."""
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(
                f"ClientId length cannot exceed {self.MAX_LENGTH} characters, "
                f"got {len(self.value)}"
            )
        if not self.value or not self.value.strip():
            raise ValueError("Client ID cannot be empty")

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


class JobState(str, Enum):
    """Job lifecycle states.

    Terminal states (COMPLETED, FAILED, CANCELLED) cannot transition.
    """

    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    def is_terminal(self) -> bool:
        """Check if state is terminal (immutable).

        Returns:
            True if state is COMPLETED, FAILED, or CANCELLED.
        """
        return self in {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}


class StageState(str, Enum):
    """Stage execution states.

    Terminal states (COMPLETED, FAILED, SKIPPED, CANCELLED) cannot transition.
    """

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"

    def is_terminal(self) -> bool:
        """Check if state is terminal (immutable).

        Returns:
            True if state is COMPLETED, FAILED, SKIPPED, or CANCELLED.
        """
        return self in {
            StageState.COMPLETED,
            StageState.FAILED,
            StageState.SKIPPED,
            StageState.CANCELLED,
        }
