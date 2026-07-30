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

"""State machine guard functions for ImageGroup lifecycle.

Defines allowed status transitions per stage and validates preconditions
before stage execution.
"""

from core.image_group.value_objects import ImageGroupStatus
from core.image_group.exceptions import (
    ImageGroupNotFoundError,
    ImageGroupMismatchError,
    InvalidStateTransitionError,
)


# Allowed status transitions per stage
# deploy accepts BUILT plus all intermediate/failed states to support
# retry and redeploy after a failed or interrupted pipeline run.
# PASSED and CLEANED are excluded — those require a fresh build first.
ALLOWED_TRANSITIONS = {
    "deploy": {
        ImageGroupStatus.BUILT,
        ImageGroupStatus.DEPLOYING,
        ImageGroupStatus.DEPLOYED,
        ImageGroupStatus.RESTARTING,
        ImageGroupStatus.RESTARTED,
        ImageGroupStatus.VALIDATING,
        ImageGroupStatus.FAILED,
    },
    "restart": {ImageGroupStatus.DEPLOYED},
    "validate": {ImageGroupStatus.RESTARTED},
    "cleanup": {
        ImageGroupStatus.BUILT,
        ImageGroupStatus.PASSED,
        ImageGroupStatus.FAILED,
    },
}

# Status flow per stage (on_start, on_success, on_failure)
STATUS_FLOW = {
    "deploy": (
        ImageGroupStatus.DEPLOYING,
        ImageGroupStatus.DEPLOYED,
        ImageGroupStatus.FAILED,
    ),
    "restart": (
        ImageGroupStatus.RESTARTING,
        ImageGroupStatus.RESTARTED,
        ImageGroupStatus.FAILED,
    ),
    "validate": (
        ImageGroupStatus.VALIDATING,
        ImageGroupStatus.PASSED,
        ImageGroupStatus.FAILED,
    ),
}


def guard_check(
    image_group,
    stage_name: str,
    requested_image_group_id: str = None,
) -> None:
    """Validate preconditions for a stage execution.

    Args:
        image_group: The ImageGroup entity (or None if not found).
        stage_name: The stage being executed (deploy, restart, validate, cleanup).
        requested_image_group_id: For deploy stage only — must match.

    Raises:
        ImageGroupNotFoundError: No ImageGroup for this Job (404).
        ImageGroupMismatchError: ID mismatch on deploy (409).
        InvalidStateTransitionError: Wrong status (412).
    """
    if image_group is None:
        raise ImageGroupNotFoundError("unknown")

    # Deploy stage: verify ID match (1:1 mapping)
    if requested_image_group_id is not None:
        if str(image_group.id) != requested_image_group_id:
            raise ImageGroupMismatchError(
                supplied=requested_image_group_id,
                expected=str(image_group.id),
            )

    # Status precondition check
    required = ALLOWED_TRANSITIONS.get(stage_name, set())
    if image_group.status not in required:
        raise InvalidStateTransitionError(
            current=image_group.status.value,
            required={s.value for s in required},
        )
