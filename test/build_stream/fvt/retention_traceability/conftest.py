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

"""State shared by retention & traceability FVT tests.

Resolves a deployed job and its image group(s) from test_config.yml.
Tests in this suite are verification-only (read-only) — they inspect
database state, audit events, and artifact metadata produced by a
prior build+deploy pipeline run.
"""

import pytest

from omnia_auto import load_test_config, log
from library.functions import (
    get_image_groups_for_job,
)


class RetentionTraceabilityState:  # pylint: disable=too-few-public-methods
    """Resolved targets for retention and traceability verification."""

    job_id: str = ""
    image_group_id: str = ""
    image_group_status: str = ""
    deploy_count: int = 0
    last_deployed_at: str = ""
    created_at: str = ""


@pytest.fixture(scope="session")
def retention_state(host):
    """Resolve the configured job and its deployed image group.

    Reads ``job_id`` from ``test_config.yml``. The job must have
    completed a build+deploy pipeline so that deploy_count and
    last_deployed_at are populated.
    """
    config = load_test_config()
    job_id = str(config.get("job_id", "")).strip()
    if not job_id:
        pytest.fail(
            "retention_traceability requires job_id in test_config.yml; "
            "run the build+deploy pipeline first or enter the job_id manually"
        )

    state = RetentionTraceabilityState()
    state.job_id = job_id

    # Resolve image group for the job
    groups = get_image_groups_for_job(host, job_id)
    if not groups["success"]:
        pytest.fail(groups["error"])
    if not groups["image_groups"]:
        pytest.fail(f"No image groups found for job_id {job_id}")

    # Prefer a deployed/passed group; fall back to the first one
    deployed = [
        g for g in groups["image_groups"]
        if g.get("status") in ("DEPLOYED", "PASSED")
    ]
    target = deployed[0] if deployed else groups["image_groups"][0]

    state.image_group_id = target["id"]
    state.image_group_status = target.get("status", "")
    state.deploy_count = target.get("deploy_count", 0)
    state.last_deployed_at = target.get("last_deployed_at", "")
    state.created_at = target.get("created_at", "")

    log(
        f"Retention target: job_id={job_id}, "
        f"image_group_id={state.image_group_id}, "
        f"status={state.image_group_status}, "
        f"deploy_count={state.deploy_count}",
        "INFO",
    )
    return state
