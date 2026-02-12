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

"""Shared fixtures for artifact domain tests."""

import pytest

from core.artifacts.value_objects import (
    ArtifactDigest,
    ArtifactKey,
    ArtifactKind,
    ArtifactRef,
    StoreHint,
)


VALID_DIGEST = "a" * 64  # valid 64-char lowercase hex


@pytest.fixture
def valid_artifact_key() -> ArtifactKey:
    """A valid artifact key."""
    return ArtifactKey("catalog/abc123def456/catalog-file.bin")


@pytest.fixture
def valid_digest() -> ArtifactDigest:
    """A valid SHA-256 digest."""
    return ArtifactDigest(VALID_DIGEST)


@pytest.fixture
def valid_store_hint() -> StoreHint:
    """A valid store hint."""
    return StoreHint(
        namespace="catalog",
        label="catalog-file",
        tags={"job_id": "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"},
    )


@pytest.fixture
def valid_artifact_ref(valid_artifact_key, valid_digest) -> ArtifactRef:
    """A valid artifact reference."""
    return ArtifactRef(
        key=valid_artifact_key,
        digest=valid_digest,
        size_bytes=1024,
        uri="memory://catalog/abc123def456/catalog-file.bin",
    )
