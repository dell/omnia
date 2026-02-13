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

"""Build Image domain exceptions."""


class BuildImageDomainError(Exception):
    """Base exception for build image domain errors."""

    def __init__(self, message: str, correlation_id: str = ""):
        """Initialize domain error.

        Args:
            message: Error message.
            correlation_id: Request correlation ID for tracing.
        """
        super().__init__(message)
        self.message = message
        self.correlation_id = correlation_id


class InvalidArchitectureError(BuildImageDomainError):
    """Raised when architecture is invalid or unsupported."""


class InvalidImageKeyError(BuildImageDomainError):
    """Raised when image key is invalid."""


class InvalidFunctionalGroupsError(BuildImageDomainError):
    """Raised when functional groups are invalid."""


class InventoryHostMissingError(BuildImageDomainError):
    """Raised when inventory host is missing from configuration."""
