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

# pylint: disable=missing-function-docstring

from core.catalog.exceptions import (
    CatalogParseError,
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
