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

"""Infrastructure layer for JobId/UUID generation using UUID v4."""

import uuid

from core.jobs.exceptions import JobDomainError
from core.jobs.repositories import JobIdGenerator, UUIDGenerator
from core.jobs.value_objects import JobId


class JobUUIDGenerator(JobIdGenerator):  # pylint: disable=R0903
    """JobId generator using UUID v4."""

    def generate(self) -> JobId:
        """Generate a new JobId using UUID v4.
        
        Returns:
            JobId: A new job identifier.
            
        Raises:
            JobDomainError: If JobId generation fails.
        """
        try:
            return JobId(str(uuid.uuid4()))
        except ValueError:
            raise
        except Exception as exc:
            raise JobDomainError(f"Failed to generate JobId: {exc}") from exc


class UUIDv4Generator(UUIDGenerator):  # pylint: disable=R0903
    """UUID v4 generator for general purpose use (returns uuid.UUID)."""

    def generate(self) -> uuid.UUID:
        """Generate a new UUID v4.
        
        Returns:
            uuid.UUID: A new UUID v4 instance.
        """
        return uuid.uuid4()
