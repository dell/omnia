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

"""Artifact domain module for Build Stream."""

from .value_objects import (
    ArtifactKey,
    ArtifactDigest,
    ArtifactRef,
    ArtifactKind,
    StoreHint,
    SafePath,
)
from .exceptions import (
    ArtifactDomainError,
    ArtifactNotFoundError,
    ArtifactAlreadyExistsError,
    ArtifactStoreError,
    ArtifactValidationError,
)
from .entities import ArtifactRecord
from .ports import ArtifactStore, ArtifactMetadataRepository

__all__ = [
    "ArtifactKey",
    "ArtifactDigest",
    "ArtifactRef",
    "ArtifactKind",
    "StoreHint",
    "SafePath",
    "ArtifactDomainError",
    "ArtifactNotFoundError",
    "ArtifactAlreadyExistsError",
    "ArtifactStoreError",
    "ArtifactValidationError",
    "ArtifactRecord",
    "ArtifactStore",
    "ArtifactMetadataRepository",
]
