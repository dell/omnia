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

"""
Orchestrator Validate — Slurm Node and Partition Validation.

TC_SL_010: Verify Slurm nodes are registered in cluster
TC_SL_011: Verify Slurm partitions are configured
TC_SL_013: Verify basic Slurm job submission works
"""

import pytest

from library.functions import TestLogger
from library.functions.slurm_func import (
    check_slurm_enabled,
    check_slurm_nodes_registered,
    check_slurm_partitions_exist,
    check_slurm_job_submission,
)
from library.messages import (
    SLURM_TEST_LOG_MSGS as LOG,
    SLURM_TEST_ASSERT_MSGS as ASSERT,
)
from library.vars.slurm_vars import TEST_CASES as TC


def _skip_if_slurm_disabled(host):
    """Skip test if Slurm is not enabled in catalog."""
    result = check_slurm_enabled(host)
    if result.get("skipped"):
        pytest.skip(result["details"])


@pytest.mark.slurm
@pytest.mark.sanity
@pytest.mark.order(1)
def test_slurm_nodes_registered(host):
    """TC_SL_010: Verify Slurm nodes are registered in cluster."""
    _skip_if_slurm_disabled(host)

    tc = TC["slurm_nodes_registered"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking SLURM node registration")
    result = check_slurm_nodes_registered(host)

    if result["success"]:
        tl.passed(LOG["slurm_nodes_registered_ok"], result["details"])
    else:
        tl.failed(LOG["slurm_nodes_registered_failed"], result["error"])

    assert result["success"], ASSERT["slurm_nodes_registered_failed"]


@pytest.mark.slurm
@pytest.mark.sanity
@pytest.mark.order(2)
def test_slurm_partitions_exist(host):
    """TC_SL_011: Verify Slurm partitions are configured."""
    _skip_if_slurm_disabled(host)

    tc = TC["slurm_partitions_exist"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Checking SLURM partitions")
    result = check_slurm_partitions_exist(host)

    if result["success"]:
        tl.passed(LOG["slurm_partitions_ok"], result["details"])
    else:
        tl.failed(LOG["slurm_partitions_failed"], result["error"])

    assert result["success"], ASSERT["slurm_partitions_failed"]


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(3)
def test_slurm_job_submission(host):
    """TC_SL_013: Verify basic Slurm job submission works."""
    _skip_if_slurm_disabled(host)

    tc = TC["slurm_job_submission"]
    tl = TestLogger(tc["title"], tc["id"])

    tl.check("Testing basic SLURM job submission")
    result = check_slurm_job_submission(host)

    if result["success"]:
        tl.passed(LOG["slurm_job_submission_ok"], result["details"])
    else:
        tl.failed(LOG["slurm_job_submission_failed"], result["error"])

    assert result["success"], ASSERT["slurm_job_submission_failed"]
