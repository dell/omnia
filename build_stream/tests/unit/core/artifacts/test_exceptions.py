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

"""Unit tests for Artifact domain exceptions."""

import pytest

from core.artifacts.exceptions import (
    ArtifactAlreadyExistsError,
    ArtifactDomainError,
    ArtifactNotFoundError,
    ArtifactStoreError,
    ArtifactValidationError,
)


class TestArtifactDomainError:
    """Tests for ArtifactDomainError base exception."""

    def test_base_error_with_message_only(self) -> None:
        error = ArtifactDomainError("Test message")
        assert error.message == "Test message"
        assert error.correlation_id is None
        assert str(error) == "Test message"

    def test_base_error_with_correlation_id(self) -> None:
        correlation_id = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
        error = ArtifactDomainError("Test message", correlation_id)
        assert error.message == "Test message"
        assert error.correlation_id == correlation_id
        assert str(error) == "Test message"

    def test_inheritance_from_exception(self) -> None:
        error = ArtifactDomainError("Test")
        assert isinstance(error, Exception)
        assert isinstance(error, ArtifactDomainError)


class TestArtifactNotFoundError:
    """Tests for ArtifactNotFoundError."""

    def test_error_with_key_only(self) -> None:
        error = ArtifactNotFoundError("catalog/missing-file.json")
        assert error.key == "catalog/missing-file.json"
        assert error.correlation_id is None
        assert "Artifact not found: catalog/missing-file.json" in str(error)

    def test_error_with_correlation_id(self) -> None:
        correlation_id = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
        error = ArtifactNotFoundError("catalog/missing-file.json", correlation_id)
        assert error.key == "catalog/missing-file.json"
        assert error.correlation_id == correlation_id
        assert error.correlation_id == correlation_id

    def test_inheritance_from_domain_error(self) -> None:
        error = ArtifactNotFoundError("test-key")
        assert isinstance(error, ArtifactDomainError)
        assert isinstance(error, Exception)


class TestArtifactAlreadyExistsError:
    """Tests for ArtifactAlreadyExistsError."""

    def test_error_with_key_only(self) -> None:
        error = ArtifactAlreadyExistsError("catalog/existing-file.json")
        assert error.key == "catalog/existing-file.json"
        assert error.correlation_id is None
        assert "Artifact already exists: catalog/existing-file.json" in str(error)

    def test_error_with_correlation_id(self) -> None:
        correlation_id = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
        error = ArtifactAlreadyExistsError("catalog/existing-file.json", correlation_id)
        assert error.key == "catalog/existing-file.json"
        assert error.correlation_id == correlation_id

    def test_inheritance_from_domain_error(self) -> None:
        error = ArtifactAlreadyExistsError("test-key")
        assert isinstance(error, ArtifactDomainError)
        assert isinstance(error, Exception)


class TestArtifactStoreError:
    """Tests for ArtifactStoreError."""

    def test_error_with_message_only(self) -> None:
        error = ArtifactStoreError("Store connection failed")
        assert error.message == "Store connection failed"
        assert error.correlation_id is None
        assert "Store connection failed" in str(error)

    def test_error_with_correlation_id(self) -> None:
        correlation_id = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
        error = ArtifactStoreError("Store connection failed", correlation_id)
        assert error.message == "Store connection failed"
        assert error.correlation_id == correlation_id

    def test_inheritance_from_domain_error(self) -> None:
        error = ArtifactStoreError("Store error")
        assert isinstance(error, ArtifactDomainError)
        assert isinstance(error, Exception)


class TestArtifactValidationError:
    """Tests for ArtifactValidationError."""

    def test_error_with_message_only(self) -> None:
        error = ArtifactValidationError("File size exceeds limit")
        assert error.message == "File size exceeds limit"
        assert error.correlation_id is None
        assert "File size exceeds limit" in str(error)

    def test_error_with_correlation_id(self) -> None:
        correlation_id = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
        error = ArtifactValidationError("File size exceeds limit", correlation_id)
        assert error.message == "File size exceeds limit"
        assert error.correlation_id == correlation_id

    def test_inheritance_from_domain_error(self) -> None:
        error = ArtifactValidationError("Validation error")
        assert isinstance(error, ArtifactDomainError)
        assert isinstance(error, Exception)
