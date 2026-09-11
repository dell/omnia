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
Orchestrator Check — Slurm Advanced Functional Tests.

Advanced SLURM tests for orchestrator test automation.
Tests cover job execution, queueing, drain/undrain, LDAP integration,
GPU resources, InfiniBand, and MPI.

ORCH_FVT_SLURM_V028: Verify slurmctld active on all control nodes
ORCH_FVT_SLURM_V029: Verify slurmd active on all compute nodes
ORCH_FVT_SLURM_V030: Verify munge active on all required nodes
ORCH_FVT_SLURM_V031: Verify srun job execution
ORCH_FVT_SLURM_V032: Verify sbatch job submission and execution
ORCH_FVT_SLURM_V033: Verify job queuing mechanism
ORCH_FVT_SLURM_V034: Verify drain and undrain functionality
ORCH_FVT_SLURM_V035: Verify LDAP user login to login nodes
ORCH_FVT_SLURM_V036: Verify LDAP user job submission
ORCH_FVT_SLURM_V037: Verify GPU resources available in SLURM
ORCH_FVT_SLURM_V038: Verify GPU job execution
ORCH_FVT_SLURM_V039: Verify InfiniBand available on compute nodes
ORCH_FVT_SLURM_V040: Verify MPI available on login compiler nodes
ORCH_FVT_SLURM_V041: Verify MPI job execution
"""

import pytest

from library.functions import (
    TestLogger,
    check_slurm_enabled,
    check_slurmctld_on_control_nodes,
    check_slurmd_on_compute_nodes,
    check_munge_on_required_nodes,
    check_srun_execution,
    check_sbatch_job_submission,
    check_job_queueing,
    check_drain_undrain_nodes,
    check_ldap_user_login,
    check_ldap_job_submission,
    check_gpu_available,
    check_gpu_job_execution,
    check_infiniband_available,
    check_mpi_available,
    check_mpi_job_execution,
)
from library.vars.slurm_vars import TEST_CASES
from library.messages import (
    SLURM_TEST_LOG_MSGS,
)

LOG = SLURM_TEST_LOG_MSGS


def skip_if_slurm_disabled(host):
    """Helper to skip test if SLURM is not enabled."""
    result = check_slurm_enabled(host)
    if result.get("skipped"):
        pytest.skip(result["details"])
    return result


def skip_if_not_applicable(result):
    """Skip an optional runtime check when its prerequisite is absent."""
    if result.get("skipped"):
        pytest.skip(result.get("details", "Runtime prerequisite is absent"))


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(20)
def test_slurmctld_on_control_nodes(host):
    """ORCH_FVT_SLURM_V028: Verify slurmctld active on all control nodes."""
    skip_if_slurm_disabled(host)

    tl = TestLogger(
        TEST_CASES["slurmctld_on_control_nodes"]["title"],
        TEST_CASES["slurmctld_on_control_nodes"]["id"]
    )

    result = check_slurmctld_on_control_nodes(host)
    skip_if_not_applicable(result)

    if result["success"]:
        tl.passed(LOG["slurmctld_check_ok"], result["details"])
    else:
        tl.failed(
            LOG["slurmctld_check_failed"].format(
                nodes=result.get("failed_nodes", [])
            ),
            result["error"],
        )

    assert result["success"], result["error"]


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(21)
def test_slurmd_on_compute_nodes(host):
    """ORCH_FVT_SLURM_V029: Verify slurmd active on all compute nodes."""
    skip_if_slurm_disabled(host)

    tl = TestLogger(
        TEST_CASES["slurmd_on_compute_nodes"]["title"],
        TEST_CASES["slurmd_on_compute_nodes"]["id"]
    )

    result = check_slurmd_on_compute_nodes(host)
    skip_if_not_applicable(result)

    if result["success"]:
        tl.passed(LOG["slurmd_check_ok"], result["details"])
    else:
        tl.failed(
            LOG["slurmd_check_failed"].format(
                nodes=result.get("failed_nodes", [])
            ),
            result["error"],
        )

    assert result["success"], result["error"]


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(22)
def test_munge_on_required_nodes(host):
    """ORCH_FVT_SLURM_V030: Verify munge active on all required nodes."""
    skip_if_slurm_disabled(host)

    tl = TestLogger(
        TEST_CASES["munge_on_required_nodes"]["title"],
        TEST_CASES["munge_on_required_nodes"]["id"]
    )

    result = check_munge_on_required_nodes(host)
    skip_if_not_applicable(result)

    if result["success"]:
        tl.passed(LOG["munge_check_ok"], result["details"])
    else:
        tl.failed(
            LOG["munge_check_failed"].format(
                nodes=result.get("failed_nodes", [])
            ),
            result["error"],
        )

    assert result["success"], result["error"]


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(23)
def test_srun_execution(host):
    """ORCH_FVT_SLURM_V031: Verify srun job execution."""
    skip_if_slurm_disabled(host)

    tl = TestLogger(
        TEST_CASES["srun_execution"]["title"],
        TEST_CASES["srun_execution"]["id"]
    )

    result = check_srun_execution(host)
    skip_if_not_applicable(result)

    if result["success"]:
        tl.passed(LOG["srun_check_ok"], result["details"])
    else:
        tl.failed(
            LOG["srun_check_failed"].format(error=result["error"]),
            result["details"],
        )

    assert result["success"], result["error"]


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(24)
def test_sbatch_job_submission(host):
    """ORCH_FVT_SLURM_V032: Verify sbatch job submission and execution."""
    skip_if_slurm_disabled(host)

    tl = TestLogger(
        TEST_CASES["sbatch_job_submission"]["title"],
        TEST_CASES["sbatch_job_submission"]["id"]
    )

    result = check_sbatch_job_submission(host)
    skip_if_not_applicable(result)

    if result["success"]:
        tl.passed(
            LOG["sbatch_check_ok"].format(job_id=result.get("job_id", "")),
            result["details"],
        )
    else:
        tl.failed(
            LOG["sbatch_check_failed"].format(error=result["error"]),
            result["details"],
        )

    assert result["success"], result["error"]


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(25)
def test_job_queueing(host):
    """ORCH_FVT_SLURM_V033: Verify job queuing mechanism."""
    skip_if_slurm_disabled(host)

    tl = TestLogger(
        TEST_CASES["job_queueing"]["title"],
        TEST_CASES["job_queueing"]["id"]
    )

    result = check_job_queueing(host)
    skip_if_not_applicable(result)

    if result["success"]:
        tl.passed(LOG["queue_test_ok"], result["details"])
    else:
        tl.failed(
            LOG["queue_test_failed"].format(error=result["error"]),
            result["details"],
        )

    assert result["success"], result["error"]


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(26)
def test_drain_undrain_nodes(host):
    """ORCH_FVT_SLURM_V034: Verify drain and undrain functionality."""
    skip_if_slurm_disabled(host)

    tl = TestLogger(
        TEST_CASES["drain_undrain_nodes"]["title"],
        TEST_CASES["drain_undrain_nodes"]["id"]
    )

    result = check_drain_undrain_nodes(host)
    skip_if_not_applicable(result)

    if result["success"]:
        tl.passed(LOG["drain_undrain_ok"], result["details"])
    else:
        tl.failed(
            LOG["drain_undrain_failed"].format(error=result["error"]),
            result["details"],
        )

    assert result["success"], result["error"]


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(27)
def test_ldap_user_login(host):
    """ORCH_FVT_SLURM_V035: Verify LDAP user login to login nodes."""
    skip_if_slurm_disabled(host)

    tl = TestLogger(
        TEST_CASES["ldap_user_login"]["title"],
        TEST_CASES["ldap_user_login"]["id"]
    )

    result = check_ldap_user_login(host)
    skip_if_not_applicable(result)

    if result["success"]:
        tl.passed(LOG["ldap_login_ok"], result["details"])
    else:
        tl.failed(
            LOG["ldap_login_failed"].format(error=result["error"]),
            result["details"],
        )

    assert result["success"], result["error"]


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(28)
def test_ldap_job_submission(host):
    """ORCH_FVT_SLURM_V036: Verify LDAP user job submission."""
    skip_if_slurm_disabled(host)

    tl = TestLogger(
        TEST_CASES["ldap_job_submission"]["title"],
        TEST_CASES["ldap_job_submission"]["id"]
    )

    result = check_ldap_job_submission(host)
    skip_if_not_applicable(result)

    if result["success"]:
        tl.passed(LOG["ldap_job_ok"], result["details"])
    else:
        tl.failed(
            LOG["ldap_job_failed"].format(error=result["error"]),
            result["details"],
        )

    assert result["success"], result["error"]


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(29)
def test_gpu_available(host):
    """ORCH_FVT_SLURM_V037: Verify GPU resources available in SLURM."""
    skip_if_slurm_disabled(host)

    tl = TestLogger(
        TEST_CASES["gpu_available"]["title"],
        TEST_CASES["gpu_available"]["id"]
    )

    result = check_gpu_available(host)
    skip_if_not_applicable(result)

    if result["success"]:
        tl.passed(LOG["gpu_available_ok"], result["details"])
    else:
        tl.failed(
            LOG["gpu_available_failed"].format(error=result["error"]),
            result["details"],
        )

    assert result["success"], result["error"]


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(30)
def test_gpu_job_execution(host):
    """ORCH_FVT_SLURM_V038: Verify GPU job execution."""
    skip_if_slurm_disabled(host)

    tl = TestLogger(
        TEST_CASES["gpu_job_execution"]["title"],
        TEST_CASES["gpu_job_execution"]["id"]
    )

    result = check_gpu_job_execution(host)
    skip_if_not_applicable(result)

    if result["success"]:
        tl.passed(
            LOG["gpu_job_ok"].format(job_id=result.get("job_id", "")),
            result["details"],
        )
    else:
        tl.failed(
            LOG["gpu_job_failed"].format(error=result["error"]),
            result["details"],
        )

    assert result["success"], result["error"]


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(31)
def test_infiniband_available(host):
    """ORCH_FVT_SLURM_V039: Verify InfiniBand available on compute nodes."""
    skip_if_slurm_disabled(host)

    tl = TestLogger(
        TEST_CASES["infiniband_available"]["title"],
        TEST_CASES["infiniband_available"]["id"]
    )

    result = check_infiniband_available(host)
    skip_if_not_applicable(result)

    if result["success"]:
        tl.passed(LOG["ib_available_ok"], result["details"])
    else:
        tl.failed(
            LOG["ib_available_failed"].format(error=result["error"]),
            result["details"],
        )

    assert result["success"], result["error"]


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(32)
def test_mpi_available(host):
    """ORCH_FVT_SLURM_V040: Verify MPI available on login compiler nodes."""
    skip_if_slurm_disabled(host)

    tl = TestLogger(
        TEST_CASES["mpi_available"]["title"],
        TEST_CASES["mpi_available"]["id"]
    )

    result = check_mpi_available(host)
    skip_if_not_applicable(result)

    if result["success"]:
        tl.passed(LOG["mpi_available_ok"], result["details"])
    else:
        tl.failed(
            LOG["mpi_available_failed"].format(error=result["error"]),
            result["details"],
        )

    assert result["success"], result["error"]


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(33)
def test_mpi_job_execution(host):
    """ORCH_FVT_SLURM_V041: Verify MPI job execution."""
    skip_if_slurm_disabled(host)

    tl = TestLogger(
        TEST_CASES["mpi_job_execution"]["title"],
        TEST_CASES["mpi_job_execution"]["id"]
    )

    result = check_mpi_job_execution(host)
    skip_if_not_applicable(result)

    if result["success"]:
        tl.passed(LOG["mpi_job_ok"], result["details"])
    else:
        tl.failed(
            LOG["mpi_job_failed"].format(error=result["error"]),
            result["details"],
        )

    assert result["success"], result["error"]
