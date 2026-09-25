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

"""Root-owned Slurm workload, queueing, and scheduler-state behavior."""

import pytest
from library.functions import (
    check_slurm_compiler_node_jobs,
    check_slurm_concurrent_jobs,
    check_slurm_control_node_jobs,
    check_slurm_drain_queue_recovery,
    check_slurm_insufficient_resources,
    check_slurm_job_queueing,
    check_slurm_login_node_jobs,
)

from fvt.result import verify_pxeboot


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(232)
def test_slurm_control_node_jobs(host):
    """Run one targeted job per compute from every Slurm control node."""
    verify_pxeboot(host, "slurm_basic_jobs", check_slurm_control_node_jobs)


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(233)
def test_slurm_login_node_jobs(host):
    """Run one targeted job per compute from every mapped login node."""
    verify_pxeboot(host, "slurm_login_jobs", check_slurm_login_node_jobs)


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(234)
def test_slurm_compiler_node_jobs(host):
    """Run one targeted job per compute from every login compiler node."""
    verify_pxeboot(host, "slurm_compiler_jobs", check_slurm_compiler_node_jobs)


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(235)
def test_slurm_concurrent_jobs(host):
    """Submit concurrent jobs and verify final accounting state."""
    verify_pxeboot(host, "slurm_concurrent_jobs", check_slurm_concurrent_jobs)


@pytest.mark.functional
@pytest.mark.negative
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(236)
def test_slurm_insufficient_resources(host):
    """Verify an impossible immediate allocation is rejected."""
    verify_pxeboot(
        host, "slurm_insufficient_resources", check_slurm_insufficient_resources
    )


@pytest.mark.functional
@pytest.mark.sanity
@pytest.mark.slurm
@pytest.mark.non_disruptive
@pytest.mark.order(237)
def test_slurm_job_queueing(host):
    """Saturate idle computes and verify one follower queues then completes."""
    verify_pxeboot(host, "slurm_job_queueing", check_slurm_job_queueing)


@pytest.mark.disruptive
@pytest.mark.sanity
@pytest.mark.scheduler_state
@pytest.mark.slurm
@pytest.mark.order(238)
def test_slurm_drain_queue_recovery(host):
    """Drain one compute node, verify queuing, and restore it."""
    verify_pxeboot(host, "slurm_drain_queue", check_slurm_drain_queue_recovery)
