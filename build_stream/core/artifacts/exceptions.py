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

"""Domain exceptions for Artifact aggregate."""

from typing import Optional


class ArtifactDomainError(Exception):
    """Base exception for all artifact domain errors."""

    def __init__(self, message: str, correlation_id: Optional[str] = None) -> None:
        """Initialize artifact domain error.

        Args:
            message: Human-readable error description.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(message)
        self.message = message
        self.correlation_id = correlation_id


class ArtifactNotFoundError(ArtifactDomainError):
    """Artifact does not exist in the store."""

    def __init__(
        self,
        key: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Initialize artifact not found error.

        Args:
            key: The artifact key that was not found.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(
            f"Artifact not found: {key}",
            correlation_id=correlation_id,
        )
        self.key = key


class ArtifactAlreadyExistsError(ArtifactDomainError):
    """Artifact with the given key already exists (immutability enforced)."""

    def __init__(
        self,
        key: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Initialize artifact already exists error.

        Args:
            key: The artifact key that already exists.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(
            f"Artifact already exists: {key}",
            correlation_id=correlation_id,
        )
        self.key = key


class ArtifactStoreError(ArtifactDomainError):
    """Infrastructure-level artifact store failure."""

    def __init__(
        self,
        message: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Initialize artifact store error.

        Args:
            message: Human-readable error description.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(message, correlation_id=correlation_id)


class ArtifactValidationError(ArtifactDomainError):
    """Artifact content fails validation (size, content-type, etc.)."""

    def __init__(
        self,
        message: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Initialize artifact validation error.

        Args:
            message: Human-readable validation error description.
            correlation_id: Optional correlation ID for tracing.
        """
        super().__init__(message, correlation_id=correlation_id)
