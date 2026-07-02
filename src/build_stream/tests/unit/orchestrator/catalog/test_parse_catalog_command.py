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

"""Unit tests for ParseCatalogCommand."""

from dataclasses import FrozenInstanceError

import pytest

from core.jobs.value_objects import CorrelationId, JobId
from orchestrator.catalog.commands.parse_catalog import ParseCatalogCommand


VALID_JOB_ID = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"
VALID_CORRELATION_ID = "018f3c4b-2d9e-7d1a-8a2b-111111111111"


class TestParseCatalogCommand:
    """Tests for ParseCatalogCommand value object."""

    def test_valid_command(self) -> None:
        cmd = ParseCatalogCommand(
            job_id=JobId(VALID_JOB_ID),
            correlation_id=CorrelationId(VALID_CORRELATION_ID),
            filename="catalog.json",
            content=b'{"Catalog": {}}',
        )
        assert cmd.filename == "catalog.json"

    def test_empty_filename_raises(self) -> None:
        with pytest.raises(ValueError, match="filename cannot be empty"):
            ParseCatalogCommand(
                job_id=JobId(VALID_JOB_ID),
                correlation_id=CorrelationId(VALID_CORRELATION_ID),
                filename="",
                content=b"{}",
            )

    def test_filename_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="filename must be"):
            ParseCatalogCommand(
                job_id=JobId(VALID_JOB_ID),
                correlation_id=CorrelationId(VALID_CORRELATION_ID),
                filename="a" * 256,
                content=b"{}",
            )

    def test_empty_content_raises(self) -> None:
        with pytest.raises(ValueError, match="content cannot be empty"):
            ParseCatalogCommand(
                job_id=JobId(VALID_JOB_ID),
                correlation_id=CorrelationId(VALID_CORRELATION_ID),
                filename="catalog.json",
                content=b"",
            )

    def test_content_too_large_raises(self) -> None:
        with pytest.raises(ValueError, match="exceeds maximum"):
            ParseCatalogCommand(
                job_id=JobId(VALID_JOB_ID),
                correlation_id=CorrelationId(VALID_CORRELATION_ID),
                filename="catalog.json",
                content=b"x" * (5 * 1024 * 1024 + 1),
            )

    def test_immutable(self) -> None:
        cmd = ParseCatalogCommand(
            job_id=JobId(VALID_JOB_ID),
            correlation_id=CorrelationId(VALID_CORRELATION_ID),
            filename="catalog.json",
            content=b"{}",
        )
        with pytest.raises(FrozenInstanceError):
            cmd.filename = "other.json"  # type: ignore[misc]
