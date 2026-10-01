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

"""Domain exceptions for Catalog operations."""

from typing import Optional, Set


class CatalogParseError(Exception):
    """Base exception for catalog parsing failures."""

    def __init__(self, message: str, correlation_id: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.correlation_id = correlation_id


class InvalidFileFormatError(CatalogParseError):
    """Uploaded file has an invalid format (not .json)."""


class InvalidJSONError(CatalogParseError):
    """JSON content is malformed or not a dictionary."""


class InvalidCatalogFormatError(CatalogParseError):
    """Catalog JSON has invalid structure (wrong number of top-level keys, etc.)."""


class CatalogNotUploadedError(CatalogParseError):
    """No catalog has been uploaded for this job yet, or it isn't valid JSON.

    Raised by parse-catalog when it can't find a catalog artifact from the
    prior "upload" stage to check. Maps to HTTP 412 Precondition Failed.
    """


class CatalogSchemaValidationError(CatalogParseError):
    """Catalog JSON fails schema validation."""

    def __init__(
        self,
        message: str,
        schema_path: str = "",
        correlation_id: Optional[str] = None,
    ) -> None:
        super().__init__(message, correlation_id=correlation_id)
        self.schema_path = schema_path


class FileTooLargeError(CatalogParseError):
    """Uploaded file exceeds the maximum allowed size."""

    def __init__(
        self,
        actual_size: int,
        max_size: int,
        correlation_id: Optional[str] = None,
    ) -> None:
        super().__init__(
            f"File size {actual_size} bytes exceeds maximum {max_size} bytes",
            correlation_id=correlation_id,
        )
        self.actual_size = actual_size
        self.max_size = max_size


class AdapterPolicyValidationError(CatalogParseError):
    """Adapter policy fails schema validation."""

    def __init__(
        self,
        message: str,
        policy_path: str = "",
        correlation_id: Optional[str] = None,
    ) -> None:
        super().__init__(message, correlation_id=correlation_id)
        self.policy_path = policy_path


class UnsupportedSchemaVersionError(CatalogParseError):
    """Catalog schema_version is missing or not in the supported set.

    Raised during catalog parsing when the ``SchemaVersion`` field is
    absent or contains a value not recognized by this release.

    Attributes:
        schema_version: The version found (or None if missing).
        supported: Set of schema versions this release accepts.
    """

    def __init__(
        self,
        schema_version: Optional[int],
        supported: Set[int],
        correlation_id: Optional[str] = None,
    ) -> None:
        if schema_version is None:
            msg = (
                "Catalog is missing required 'SchemaVersion' field. "
                f"Supported versions: {sorted(supported)}"
            )
        else:
            msg = (
                f"Unsupported catalog schema version {schema_version}. "
                f"Supported versions: {sorted(supported)}"
            )
        super().__init__(msg, correlation_id=correlation_id)
        self.schema_version = schema_version
        self.supported = supported


class ConfigGenerationError(CatalogParseError):
    """Omnia config generation fails during adapter transformation."""
