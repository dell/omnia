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

"""Unit tests for infrastructure ID generators."""

import uuid

from infra.id_generator import JobUUIDGenerator, UUIDv4Generator


class TestJobUUIDGenerator:
    """Tests covering JobUUIDGenerator behavior (UUID v4 under the hood)."""

    def test_generate_returns_valid_job_id(self) -> None:
        """Generator should produce a JobId string of expected length."""
        generator = JobUUIDGenerator()

        job_id = generator.generate()

        assert isinstance(job_id.value, str)
        assert len(job_id.value) == 36
        # Ensure it parses as a UUID (version-agnostic acceptance)
        uuid_obj = uuid.UUID(job_id.value)
        assert isinstance(uuid_obj, uuid.UUID)

    def test_generate_is_unique(self) -> None:
        """Generator should yield unique IDs over multiple invocations."""
        generator = JobUUIDGenerator()

        generated = {generator.generate().value for _ in range(50)}

        assert len(generated) == 50


class TestUUIDv4Generator:  # pylint: disable=R0903
    """Tests covering generic UUIDv4Generator."""

    def test_generate_returns_uuid_instance(self) -> None:
        """Ensure generator returns a UUID4 instance."""
        generator = UUIDv4Generator()

        value = generator.generate()

        assert isinstance(value, uuid.UUID)
        assert value.version == 4
