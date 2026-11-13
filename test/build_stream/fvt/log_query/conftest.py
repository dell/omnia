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

"""Shared state for the pipeline log query FVT (ER-BSM-003).

Read-only tests use the completed build-pipeline job recorded as ``job_id`` in
``test_config.yml``. Tests that plant fixture logs use one disposable job and
run only when ``nft_allow_security_mutation: true`` is configured.
"""

from typing import Dict, Iterator, List

import pytest

from omnia_auto import load_test_config, log
from library.functions import nft_func
from library.functions.log_query_func import get_job, remove_planted_logs


class LogQueryState:  # pylint: disable=too-few-public-methods
    """Resolved build job and the stages that have published logs."""

    job_id: str = ""
    logged_stages: List[str] = []
    stage_lines: Dict[str, int] = {}


@pytest.fixture(scope="session")
def log_query_state(host) -> LogQueryState:
    """Resolve the configured build job and its stages with published logs."""
    job_id = str(load_test_config().get("job_id", "") or "").strip()
    if not job_id:
        pytest.fail(
            "log_query requires job_id in test_config.yml; run build_pipeline "
            "exec/test first or enter the job_id manually"
        )
    response = get_job(host, job_id)
    if response["status"] != 200 or not response["json"]:
        pytest.fail(f"GET /jobs/{job_id[:8]}... returned HTTP {response['status']}")
    state = LogQueryState()
    state.job_id = job_id
    state.stage_lines = {
        stage["stage_name"]: stage.get("log_lines", 0)
        for stage in response["json"].get("stages", [])
        if stage.get("has_log")
    }
    state.logged_stages = sorted(state.stage_lines)
    if not state.logged_stages:
        pytest.fail(
            "No stage of the configured job reports has_log=true; the BSM build does "
            "not include ER-BSM-003 or the job has no published stage logs"
        )
    log(f"log_query: job {job_id[:8]}... stages with logs: {state.logged_stages}", "INFO")
    return state


@pytest.fixture
def disposable_job(host) -> Iterator[str]:
    """Create a disposable job for fixture logs; skip unless mutation is allowed."""
    if not load_test_config().get("nft_allow_security_mutation", False):
        pytest.skip("Set nft_allow_security_mutation: true to plant fixture stage logs")
    created = nft_func.create_disposable_job(host)
    if created.get("status") != 201 or not created.get("job_id"):
        pytest.fail(f"Disposable job creation failed (HTTP {created.get('status')})")
    job_id = created["job_id"]
    try:
        yield job_id
    finally:
        remove_planted_logs(host, job_id, ["build-image", "deploy"])
