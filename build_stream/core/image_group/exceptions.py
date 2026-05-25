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

"""Domain exceptions for ImageGroup aggregate."""


class DuplicateImageGroupError(Exception):
    """Raised when an ImageGroup with the same ID already exists.

    Maps to HTTP 409 Conflict.
    """

    def __init__(self, image_group_id: str):
        self.image_group_id = image_group_id
        super().__init__(
            f"Image Group '{image_group_id}' already exists. "
            f"Each catalog can only be built once."
        )


class ImageGroupNotFoundError(Exception):
    """Raised when no ImageGroup is associated with a Job.

    Maps to HTTP 404 Not Found.
    """

    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(
            f"No Image Group associated with Job '{job_id}'"
        )


class ImageGroupMismatchError(Exception):
    """Raised when supplied image_group_id doesn't match Job's ImageGroup.

    Maps to HTTP 409 Conflict.
    """

    def __init__(self, supplied: str, expected: str):
        self.supplied = supplied
        self.expected = expected
        super().__init__(
            f"Supplied image_group_id '{supplied}' does not match "
            f"expected '{expected}'"
        )


class InvalidStateTransitionError(Exception):
    """Raised when ImageGroup is not in the required status for an operation.

    Maps to HTTP 412 Precondition Failed.
    """

    def __init__(self, current: str, required: set):
        self.current = current
        self.required = required
        super().__init__(
            f"ImageGroup status is '{current}', "
            f"required: {sorted(required)}"
        )
