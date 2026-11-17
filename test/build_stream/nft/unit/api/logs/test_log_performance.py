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

"""TC-NFT-001: log query latency budget (ER-BSM-003 NFR-1), in-process."""

import statistics
import time

import pytest

pytestmark = pytest.mark.unit

ITERATIONS = 100
LOG_QUERY_P95_BUDGET_S = 0.5
JOB_DETAIL_P95_BUDGET_S = 2.0


@pytest.fixture(autouse=True)
def _unthrottled(rate_limit):
    """Measure latency, not the 60/min limiter (which TC-FVT-017 covers separately)."""
    rate_limit["per_minute"] = 100000


def _p95(samples):
    """95th percentile of timing samples."""
    return statistics.quantiles(samples, n=100)[94]


def _time(call):
    """Run call ITERATIONS times and return the durations in seconds."""
    durations = []
    for _ in range(ITERATIONS):
        start = time.perf_counter()
        call()
        durations.append(time.perf_counter() - start)
    return durations


def test_tail_query_p95_under_500ms(client, headers, create_job, publish_log):
    """GIVEN a 5000-line stage log WHEN tail_lines=50 is queried 100x THEN P95 < 500ms."""
    job_id = create_job()
    publish_log(job_id, "build-image", "".join(f"line {i}\n" for i in range(5000)))

    def call():
        response = client.get(f"/api/v1/jobs/{job_id}/logs?tail_lines=50", headers=headers)
        assert response.status_code == 200

    assert _p95(_time(call)) < LOG_QUERY_P95_BUDGET_S


def test_job_detail_with_log_metadata_p95_under_2s(client, headers, create_job, publish_log):
    """GIVEN a job with all stages and logs WHEN GET /jobs/{id} runs 100x THEN P95 < 2s."""
    job_id = create_job()
    for stage in ("create-local-repository", "build-image", "validate", "restart", "deploy"):
        publish_log(job_id, stage, "".join(f"line {i}\n" for i in range(2000)))

    def call():
        assert client.get(f"/api/v1/jobs/{job_id}", headers=headers).status_code == 200

    assert _p95(_time(call)) < JOB_DETAIL_P95_BUDGET_S
