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

"""Unit tests for Catalog domain exceptions."""

import pytest

from core.catalog.exceptions import (
    AdapterPolicyValidationError,
    CatalogParseError,
    CatalogSchemaValidationError,
    ConfigGenerationError,
    FileTooLargeError,
    InvalidFileFormatError,
    InvalidJSONError,
)


class TestCatalogParseError:
    """Tests for CatalogParseError base exception."""

    def test_base_error_with_message_only(self) -> None:
        error = CatalogParseError("Test message")
        assert error.message == "Test message"
        assert error.correlation_id is None
        assert str(error) == "Test message"

    def test_base_error_with_correlation_id(self) -> None:
        correlation_id = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
        error = CatalogParseError("Test message", correlation_id)
        assert error.message == "Test message"
        assert error.correlation_id == correlation_id
        assert str(error) == "Test message"

    def test_inheritance_from_exception(self) -> None:
        error = CatalogParseError("Test")
        assert isinstance(error, Exception)
        assert isinstance(error, CatalogParseError)


class TestInvalidFileFormatError:
    """Tests for InvalidFileFormatError."""

    def test_error_creation(self) -> None:
        error = InvalidFileFormatError("Invalid file format")
        assert isinstance(error, CatalogParseError)
        assert isinstance(error, Exception)
        assert str(error) == "Invalid file format"

    def test_error_with_correlation_id(self) -> None:
        correlation_id = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
        error = InvalidFileFormatError("Invalid format", correlation_id)
        assert error.correlation_id == correlation_id


class TestInvalidJSONError:
    """Tests for InvalidJSONError."""

    def test_error_creation(self) -> None:
        error = InvalidJSONError("Malformed JSON")
        assert isinstance(error, CatalogParseError)
        assert isinstance(error, Exception)
        assert str(error) == "Malformed JSON"

    def test_error_with_correlation_id(self) -> None:
        correlation_id = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
        error = InvalidJSONError("JSON error", correlation_id)
        assert error.correlation_id == correlation_id


class TestCatalogSchemaValidationError:
    """Tests for CatalogSchemaValidationError."""

    def test_error_with_message_only(self) -> None:
        error = CatalogSchemaValidationError("Schema validation failed")
        assert error.message == "Schema validation failed"
        assert error.schema_path == ""
        assert error.correlation_id is None
        assert isinstance(error, CatalogParseError)

    def test_error_with_schema_path(self) -> None:
        schema_path = "/path/to/schema.json"
        error = CatalogSchemaValidationError(
            "Validation failed",
            schema_path=schema_path
        )
        assert error.message == "Validation failed"
        assert error.schema_path == schema_path
        assert error.correlation_id is None

    def test_error_with_correlation_id(self) -> None:
        correlation_id = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
        error = CatalogSchemaValidationError(
            "Validation failed",
            correlation_id=correlation_id
        )
        assert error.correlation_id == correlation_id

    def test_error_with_all_parameters(self) -> None:
        correlation_id = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
        schema_path = "/path/to/schema.json"
        error = CatalogSchemaValidationError(
            "Validation failed",
            schema_path=schema_path,
            correlation_id=correlation_id
        )
        assert error.message == "Validation failed"
        assert error.schema_path == schema_path
        assert error.correlation_id == correlation_id


class TestFileTooLargeError:
    """Tests for FileTooLargeError."""

    def test_error_creation(self) -> None:
        error = FileTooLargeError(actual_size=5000, max_size=1000)
        assert error.actual_size == 5000
        assert error.max_size == 1000
        assert error.correlation_id is None
        assert "5000 bytes exceeds maximum 1000 bytes" in str(error)
        assert isinstance(error, CatalogParseError)

    def test_error_with_correlation_id(self) -> None:
        correlation_id = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
        error = FileTooLargeError(
            actual_size=5000,
            max_size=1000,
            correlation_id=correlation_id
        )
        assert error.correlation_id == correlation_id

    def test_error_message_format(self) -> None:
        error = FileTooLargeError(actual_size=1024, max_size=512)
        expected_msg = "File size 1024 bytes exceeds maximum 512 bytes"
        assert str(error) == expected_msg


class TestAdapterPolicyValidationError:
    """Tests for AdapterPolicyValidationError."""

    def test_error_with_message_only(self) -> None:
        error = AdapterPolicyValidationError("Policy validation failed")
        assert error.message == "Policy validation failed"
        assert error.policy_path == ""
        assert error.correlation_id is None
        assert isinstance(error, CatalogParseError)

    def test_error_with_policy_path(self) -> None:
        policy_path = "/path/to/policy.json"
        error = AdapterPolicyValidationError(
            "Validation failed",
            policy_path=policy_path
        )
        assert error.message == "Validation failed"
        assert error.policy_path == policy_path
        assert error.correlation_id is None

    def test_error_with_correlation_id(self) -> None:
        correlation_id = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
        error = AdapterPolicyValidationError(
            "Validation failed",
            correlation_id=correlation_id
        )
        assert error.correlation_id == correlation_id

    def test_error_with_all_parameters(self) -> None:
        correlation_id = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
        policy_path = "/path/to/policy.json"
        error = AdapterPolicyValidationError(
            "Validation failed",
            policy_path=policy_path,
            correlation_id=correlation_id
        )
        assert error.message == "Validation failed"
        assert error.policy_path == policy_path
        assert error.correlation_id == correlation_id


class TestConfigGenerationError:
    """Tests for ConfigGenerationError."""

    def test_error_creation(self) -> None:
        error = ConfigGenerationError("Config generation failed")
        assert isinstance(error, CatalogParseError)
        assert isinstance(error, Exception)
        assert str(error) == "Config generation failed"

    def test_error_with_correlation_id(self) -> None:
        correlation_id = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
        error = ConfigGenerationError("Generation failed", correlation_id)
        assert error.correlation_id == correlation_id
