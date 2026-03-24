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

"""ValidateImageOnTest domain exceptions."""


class ValidateDomainError(Exception):
    """Base exception for validate-image-on-test domain errors."""

    def __init__(self, message: str, correlation_id: str = ""):
        """Initialize domain error.

        Args:
            message: Error message.
            correlation_id: Request correlation ID for tracing.
        """
        super().__init__(message)
        self.message = message
        self.correlation_id = correlation_id


class EnvironmentUnavailableError(ValidateDomainError):
    """Raised when test environment is not available for validation."""


class ValidationExecutionError(ValidateDomainError):
    """Raised when validation playbook execution fails."""


class StageGuardViolationError(ValidateDomainError):
    """Raised when required upstream stage has not completed."""
