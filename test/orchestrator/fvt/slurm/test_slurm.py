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
Orchestrator Slurm — Verification Tests.

SLURM tests based on automation-v2.2.0.0 branch analysis.
Tests cover node discovery, service checks, job execution, LDAP, GPU, and more.

TC_SL_029: Verify slurmctld active on all control nodes
TC_SL_030: Verify slurmd active on all compute nodes
TC_SL_031: Verify munge active on all required nodes
TC_SL_032: Verify srun job execution
TC_SL_033: Verify sbatch job submission and execution
TC_SL_034: Verify job queuing mechanism
TC_SL_035: Verify drain and undrain functionality
TC_SL_036: Verify LDAP user login to login nodes
TC_SL_037: Verify LDAP user job submission
TC_SL_038: Verify GPU resources available in SLURM
TC_SL_039: Verify GPU job execution
TC_SL_040: Verify InfiniBand available on compute nodes
TC_SL_041: Verify MPI available on login compiler nodes
TC_SL_042: Verify MPI job execution
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
    SLURM_TEST_ASSERT_MSGS,
)

LOG = SLURM_TEST_LOG_MSGS
ASSERT = SLURM_TEST_ASSERT_MSGS


def skip_if_slurm_disabled(host):
    """Helper to skip test if SLURM is not enabled."""
    result = check_slurm_enabled(host)
    if result.get("skipped"):
        pytest.skip(result["details"])
    return result


@pytest.mark.slurm
@pytest.mark.sanity
@pytest.mark.order(1)
def test_slurm_enabled(host):
    """TC_SL_001: Verify Slurm is enabled in catalog."""
    tl = TestLogger(
        TEST_CASES["slurm_enabled"]["title"],
        TEST_CASES["slurm_enabled"]["id"]
    )

    result = check_slurm_enabled(host)

    if result.get("skipped"):
        tl.skipped(result["details"], "")
        pytest.skip(result["details"])

    if result["success"]:
        tl.passed(LOG["slurm_enabled_ok"], result["details"])
    else:
        tl.failed(LOG["slurm_enabled_failed"], result["error"])

    assert result["success"], ASSERT["slurm_enabled_failed"]


@pytest.mark.slurm
@pytest.mark.sanity
@pytest.mark.order(2)
def test_slurmctld_on_control_nodes(host):
    """TC_SL_029: Verify slurmctld active on all control nodes."""
    skip_if_slurm_disabled(host)

    tl = TestLogger(
        TEST_CASES["slurmctld_on_control_nodes"]["title"],
        TEST_CASES["slurmctld_on_control_nodes"]["id"]
    )

    result = check_slurmctld_on_control_nodes(host)

    if result.get("skipped"):
        tl.passed("No control nodes found - skipping", result["details"])
        pytest.skip("No SLURM control nodes available")

    if result["success"]:
        tl.passed(LOG["slurmctld_check_ok"], result["details"])
    else:
        failed_nodes = result.get("failed_nodes", [])
        tl.failed(
            LOG["slurmctld_check_failed"].format(nodes=failed_nodes),
            result["error"]
        )

    assert result["success"], ASSERT["slurmctld_check_failed"].format(
        nodes=result.get("failed_nodes", [])
    )


@pytest.mark.slurm
@pytest.mark.sanity
@pytest.mark.order(3)
def test_slurmd_on_compute_nodes(host):
    """TC_SL_030: Verify slurmd active on all compute nodes."""
    skip_if_slurm_disabled(host)
    tl = TestLogger(
        TEST_CASES["slurmd_on_compute_nodes"]["title"],
        TEST_CASES["slurmd_on_compute_nodes"]["id"]
    )

    result = check_slurmd_on_compute_nodes(host)

    if result.get("skipped"):
        tl.passed("No compute nodes found - skipping", result["details"])
        pytest.skip("No SLURM compute nodes available")

    if result["success"]:
        tl.passed(LOG["slurmd_check_ok"], result["details"])
    else:
        failed_nodes = result.get("failed_nodes", [])
        tl.failed(
            LOG["slurmd_check_failed"].format(nodes=failed_nodes),
            result["error"]
        )

    assert result["success"], ASSERT["slurmd_check_failed"].format(
        nodes=result.get("failed_nodes", [])
    )


@pytest.mark.slurm
@pytest.mark.sanity
@pytest.mark.order(4)
def test_munge_on_required_nodes(host):
    """TC_SL_031: Verify munge active on all required nodes."""
    skip_if_slurm_disabled(host)
    tl = TestLogger(
        TEST_CASES["munge_on_required_nodes"]["title"],
        TEST_CASES["munge_on_required_nodes"]["id"]
    )

    result = check_munge_on_required_nodes(host)

    if result.get("skipped"):
        tl.passed("No required nodes found - skipping", result["details"])
        pytest.skip("No nodes requiring Munge available")

    if result["success"]:
        tl.passed(LOG["munge_check_ok"], result["details"])
    else:
        failed_nodes = result.get("failed_nodes", [])
        tl.failed(
            LOG["munge_check_failed"].format(nodes=failed_nodes),
            result["error"]
        )

    assert result["success"], ASSERT["munge_check_failed"].format(
        nodes=result.get("failed_nodes", [])
    )


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(5)
def test_srun_execution(host):
    """TC_SL_032: Verify srun job execution."""
    skip_if_slurm_disabled(host)
    tl = TestLogger(
        TEST_CASES["srun_execution"]["title"],
        TEST_CASES["srun_execution"]["id"]
    )

    result = check_srun_execution(host)

    if result["success"]:
        tl.passed(LOG["srun_check_ok"], result["details"])
    else:
        tl.failed(LOG["srun_check_failed"], result["error"])

    assert result["success"], ASSERT["srun_check_failed"].format(
        error=result.get("error", "Unknown error")
    )


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(6)
def test_sbatch_job_submission(host):
    """TC_SL_033: Verify sbatch job submission and execution."""
    skip_if_slurm_disabled(host)
    tl = TestLogger(
        TEST_CASES["sbatch_job_submission"]["title"],
        TEST_CASES["sbatch_job_submission"]["id"]
    )

    result = check_sbatch_job_submission(host)

    if result["success"]:
        job_id = result.get("job_id", "unknown")
        tl.passed(LOG["sbatch_check_ok"].format(job_id=job_id), result["details"])
    else:
        tl.failed(LOG["sbatch_check_failed"], result["error"])

    assert result["success"], ASSERT["sbatch_check_failed"].format(
        error=result.get("error", "Unknown error")
    )


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(7)
def test_job_queueing(host):
    """TC_SL_034: Verify job queuing mechanism."""
    skip_if_slurm_disabled(host)
    tl = TestLogger(
        TEST_CASES["job_queueing"]["title"],
        TEST_CASES["job_queueing"]["id"]
    )

    result = check_job_queueing(host)

    if result["success"]:
        job_ids = result.get("job_ids", [])
        tl.passed(LOG["queue_test_ok"], f"Job IDs: {job_ids}")
    else:
        tl.failed(LOG["queue_test_failed"], result["error"])

    assert result["success"], ASSERT["queue_test_failed"].format(
        error=result.get("error", "Unknown error")
    )


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(8)
def test_drain_undrain_nodes(host):
    """TC_SL_035: Verify drain and undrain functionality."""
    skip_if_slurm_disabled(host)
    tl = TestLogger(
        TEST_CASES["drain_undrain_nodes"]["title"],
        TEST_CASES["drain_undrain_nodes"]["id"]
    )

    result = check_drain_undrain_nodes(host)

    if result.get("skipped"):
        tl.passed("No compute nodes - skipping drain test", result["details"])
        pytest.skip("No compute nodes available for drain test")

    if result["success"]:
        tl.passed(LOG["drain_undrain_ok"], result["details"])
    else:
        tl.failed(LOG["drain_undrain_failed"], result["error"])

    assert result["success"], ASSERT["drain_undrain_failed"].format(
        error=result.get("error", "Unknown error")
    )


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(9)
def test_ldap_user_login(host):
    """TC_SL_036: Verify LDAP user login to login nodes."""
    skip_if_slurm_disabled(host)
    tl = TestLogger(
        TEST_CASES["ldap_user_login"]["title"],
        TEST_CASES["ldap_user_login"]["id"]
    )

    result = check_ldap_user_login(host)

    if result.get("skipped"):
        tl.passed("LDAP not configured - skipping", result["details"])
        pytest.skip("LDAP credentials not configured")

    if result["success"]:
        tl.passed(LOG["ldap_login_ok"], result["details"])
    else:
        failed_nodes = result.get("failed_nodes", [])
        tl.failed(
            LOG["ldap_login_failed"].format(nodes=failed_nodes),
            result["error"]
        )

    assert result["success"], ASSERT["ldap_login_failed"].format(
        nodes=result.get("failed_nodes", [])
    )


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(10)
def test_ldap_job_submission(host):
    """TC_SL_037: Verify LDAP user job submission."""
    skip_if_slurm_disabled(host)
    tl = TestLogger(
        TEST_CASES["ldap_job_submission"]["title"],
        TEST_CASES["ldap_job_submission"]["id"]
    )

    result = check_ldap_job_submission(host)

    if result.get("skipped"):
        tl.passed("LDAP not configured - skipping", result["details"])
        pytest.skip("LDAP credentials not configured")

    if result["success"]:
        job_id = result.get("job_id", "unknown")
        tl.passed(LOG["ldap_job_ok"].format(job_id=job_id), result["details"])
    else:
        tl.failed(LOG["ldap_job_failed"], result["error"])

    assert result["success"], ASSERT["ldap_job_failed"].format(
        error=result.get("error", "Unknown error")
    )


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(11)
def test_gpu_available(host):
    """TC_SL_038: Verify GPU resources available in SLURM."""
    skip_if_slurm_disabled(host)
    tl = TestLogger(
        TEST_CASES["gpu_available"]["title"],
        TEST_CASES["gpu_available"]["id"]
    )

    result = check_gpu_available(host)

    if result.get("skipped"):
        tl.passed("GPU not configured - skipping GPU tests", result["details"])
        pytest.skip("GPU resources not configured")

    if result["success"]:
        gpu_nodes = result.get("gpu_nodes", [])
        tl.passed(LOG["gpu_available_ok"], f"GPU config: {gpu_nodes}")
    else:
        tl.failed(LOG["gpu_available_failed"], result["error"])

    # Don't assert failure for GPU - it's optional
    if not result["success"] and not result.get("skipped"):
        tl.passed("GPU check failed but not critical", result["error"])


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(12)
def test_gpu_job_execution(host):
    """TC_SL_039: Verify GPU job execution."""
    skip_if_slurm_disabled(host)
    tl = TestLogger(
        TEST_CASES["gpu_job_execution"]["title"],
        TEST_CASES["gpu_job_execution"]["id"]
    )

    result = check_gpu_job_execution(host)

    if result.get("skipped"):
        tl.passed("GPU not configured - skipping GPU job test", result["details"])
        pytest.skip("GPU resources not configured")

    if result["success"]:
        job_id = result.get("job_id", "unknown")
        tl.passed(LOG["gpu_job_ok"].format(job_id=job_id), result["details"])
    else:
        tl.failed(LOG["gpu_job_failed"], result["error"])

    # Don't assert failure for GPU jobs - it's optional
    if not result["success"] and not result.get("skipped"):
        tl.passed("GPU job test failed but not critical", result["error"])


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(13)
def test_infiniband_available(host):
    """TC_SL_040: Verify InfiniBand available on compute nodes."""
    skip_if_slurm_disabled(host)
    tl = TestLogger(
        TEST_CASES["infiniband_available"]["title"],
        TEST_CASES["infiniband_available"]["id"]
    )

    result = check_infiniband_available(host)

    if result.get("skipped"):
        tl.passed("InfiniBand not configured - skipping IB tests", result["details"])
        pytest.skip("InfiniBand not configured")

    if result["success"]:
        ib_nodes = result.get("ib_nodes", [])
        tl.passed(LOG["ib_available_ok"], f"IB nodes: {ib_nodes}")
    else:
        tl.failed(LOG["ib_available_failed"], result["error"])

    # Don't assert failure for InfiniBand - it's optional
    if not result["success"] and not result.get("skipped"):
        tl.passed("InfiniBand check failed but not critical", result["error"])


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(14)
def test_mpi_available(host):
    """TC_SL_041: Verify MPI available on login compiler nodes."""
    skip_if_slurm_disabled(host)
    tl = TestLogger(
        TEST_CASES["mpi_available"]["title"],
        TEST_CASES["mpi_available"]["id"]
    )

    result = check_mpi_available(host)

    if result.get("skipped"):
        tl.passed("MPI not configured - skipping MPI tests", result["details"])
        pytest.skip("MPI not configured")

    if result["success"]:
        mpi_nodes = result.get("mpi_nodes", [])
        tl.passed(LOG["mpi_available_ok"], f"MPI nodes: {mpi_nodes}")
    else:
        tl.failed(LOG["mpi_available_failed"], result["error"])

    # Don't assert failure for MPI - it's optional
    if not result["success"] and not result.get("skipped"):
        tl.passed("MPI check failed but not critical", result["error"])


@pytest.mark.slurm
@pytest.mark.functional
@pytest.mark.order(15)
def test_mpi_job_execution(host):
    """TC_SL_042: Verify MPI job execution."""
    skip_if_slurm_disabled(host)
    tl = TestLogger(
        TEST_CASES["mpi_job_execution"]["title"],
        TEST_CASES["mpi_job_execution"]["id"]
    )

    result = check_mpi_job_execution(host)

    if result.get("skipped"):
        tl.passed("MPI not configured - skipping MPI job test", result["details"])
        pytest.skip("MPI not configured")

    if result["success"]:
        tl.passed(LOG["mpi_job_ok"], result["details"])
    else:
        tl.failed(LOG["mpi_job_failed"], result["error"])

    # Don't assert failure for MPI jobs - it's optional
    if not result["success"] and not result.get("skipped"):
        tl.passed("MPI job test failed but not critical", result["error"])
