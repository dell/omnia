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

"""Shared fixtures for artifact store infrastructure tests."""

import pytest

from core.artifacts.value_objects import ArtifactKind, StoreHint
from infra.artifact_store.in_memory_artifact_store import InMemoryArtifactStore
from infra.artifact_store.in_memory_artifact_metadata import (
    InMemoryArtifactMetadataRepository,
)


@pytest.fixture
def artifact_store() -> InMemoryArtifactStore:
    """Fresh in-memory artifact store."""
    return InMemoryArtifactStore()


@pytest.fixture
def artifact_metadata_repo() -> InMemoryArtifactMetadataRepository:
    """Fresh in-memory artifact metadata repository."""
    return InMemoryArtifactMetadataRepository()


@pytest.fixture
def file_hint() -> StoreHint:
    """Store hint for a FILE artifact."""
    return StoreHint(
        namespace="catalog",
        label="catalog-file",
        tags={"job_id": "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"},
    )


@pytest.fixture
def archive_hint() -> StoreHint:
    """Store hint for an ARCHIVE artifact."""
    return StoreHint(
        namespace="catalog",
        label="root-jsons",
        tags={"job_id": "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"},
    )


@pytest.fixture
def sample_content() -> bytes:
    """Sample file content."""
    return b'{"name": "test-catalog", "version": "1.0"}'


@pytest.fixture
def sample_file_map() -> dict:
    """Sample file map for archive storage."""
    return {
        "x86_64/rhel/9.5/functional_layer.json": b'{"features": []}',
        "x86_64/rhel/9.5/base_os.json": b'{"packages": []}',
    }
