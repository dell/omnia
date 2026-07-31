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
"""
Custom exception classes for Config Editor Module

Provides domain-specific exceptions for better error handling and user feedback.
"""

from typing import Any, Dict, Optional


class ConfigEditorException(Exception):
    """Base exception for Config Editor errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AdapterPolicyNotFoundError(ConfigEditorException):
    """Raised when an adapter policy is not found."""

    def __init__(
        self,
        policy_type: str = "custom",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            f"Adapter policy not found: {policy_type}",
            status_code=404,
            details=details
        )
        self.policy_type = policy_type


class GenerationError(ConfigEditorException):
    """Raised when configuration generation fails."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            f"Configuration generation failed: {message}",
            status_code=500,
            details=details
        )
