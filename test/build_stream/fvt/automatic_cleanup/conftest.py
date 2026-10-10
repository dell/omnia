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

"""Shared state for explicit automatic-cleanup FVT execution."""

import os

import pytest

from omnia_auto import load_test_config
from library.functions import get_image_groups_for_job, get_images_for_job


class AutomaticCleanupState:  # pylint: disable=too-few-public-methods
    """Exact automatic-cleanup target selected by configuration."""

    job_id = ""
    image_group_id = ""
    roles = []


@pytest.fixture(scope="session")
def automatic_cleanup_state(host):
    """Resolve only the explicitly configured automatic-cleanup target."""
    config = load_test_config()
    state = AutomaticCleanupState()
    state.job_id = str(config.get("automatic_cleanup_job_id", "")).strip()
    if not state.job_id:
        pytest.fail(
            "automatic_cleanup requires automatic_cleanup_job_id in "
            "test_config.yml; use a dedicated Job whose ImageGroup is FAILED"
        )
    if (
        os.environ.get("OMNIA_COMMAND_TYPE", "") == "exec"
        and not config.get("automatic_cleanup_allow_execution", False)
    ):
        pytest.fail(
            "Set automatic_cleanup_allow_execution: true only after confirming "
            "the configured Job is the sole FAILED ImageGroup"
        )

    groups = get_image_groups_for_job(host, state.job_id)
    if not groups["success"]:
        pytest.fail(groups["error"])
    if len(groups["image_groups"]) != 1:
        pytest.fail(
            f"Expected exactly one ImageGroup for {state.job_id}, found "
            f"{len(groups['image_groups'])}"
        )
    state.image_group_id = groups["image_groups"][0]["id"]

    images = get_images_for_job(host, state.job_id)
    if not images["success"]:
        pytest.fail(images["error"])
    state.roles = sorted({
        image["role"] for image in images["images"] if image.get("role")
    })
    if not state.roles:
        pytest.fail(f"No image roles exist for automatic cleanup Job {state.job_id}")
    return state
