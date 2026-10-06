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

"""HPC benchmarks destructive checks (gated by ``--run-destructive``).

Each test in this module mutates cluster state (executes pull_benchmarks.sh,
probes external egress, or diffs /hpc_tools snapshots) and is therefore
skipped by default. Enable with either:

    pytest --run-destructive orchestrator/fvt/pxeboot/slurm_hpc_benchmarks/

or by exporting ``OMNIA_HPC_BENCHMARKS_DESTRUCTIVE=1`` before the run. The
gate is implemented in the suite-local conftest so no other suite is
affected.

Includes the adjacent-flow invariance checks (TC-14 through TC-17) which
run ``pull_benchmarks.sh`` to verify that staging does not disturb CUDA,
NVHPC, container-image, or OpenMPI/UCX directories.
"""

import pytest
from library.functions import (
    check_hpc_benchmarks_airgapped_staging,
    check_hpc_benchmarks_container_image_unaffected,
    check_hpc_benchmarks_cuda_flow_unaffected,
    check_hpc_benchmarks_existing_dirs_preserved,
    check_hpc_benchmarks_nvhpc_flow_unaffected,
    check_hpc_benchmarks_openmpi_unaffected,
    check_hpc_benchmarks_per_tool_staging_report,
    check_hpc_benchmarks_staging_idempotency,
)

from fvt.result import verify_pxeboot

pytestmark = [pytest.mark.slurm, pytest.mark.destructive]


# --- Invariance checks (staging run + snapshot diff) ---


@pytest.mark.functional
@pytest.mark.order(342)
def test_hpc_benchmarks_cuda_flow_unaffected(host):
    """TC-14: Verify /hpc_tools/cuda is unchanged after benchmark staging."""
    verify_pxeboot(
        host,
        "hpc_benchmarks_cuda_flow_unaffected",
        check_hpc_benchmarks_cuda_flow_unaffected,
    )


@pytest.mark.functional
@pytest.mark.order(343)
def test_hpc_benchmarks_nvhpc_flow_unaffected(host):
    """TC-15: Verify /hpc_tools/nvidia_sdk is unchanged after staging."""
    verify_pxeboot(
        host,
        "hpc_benchmarks_nvhpc_flow_unaffected",
        check_hpc_benchmarks_nvhpc_flow_unaffected,
    )


@pytest.mark.functional
@pytest.mark.order(344)
def test_hpc_benchmarks_container_image_unaffected(host):
    """TC-16: Verify /hpc_tools/container_images is unchanged after staging."""
    verify_pxeboot(
        host,
        "hpc_benchmarks_container_image_unaffected",
        check_hpc_benchmarks_container_image_unaffected,
    )


@pytest.mark.functional
@pytest.mark.order(345)
def test_hpc_benchmarks_openmpi_unaffected(host):
    """TC-17: Verify OpenMPI/UCX discovery is stable across a staging run."""
    verify_pxeboot(
        host,
        "hpc_benchmarks_openmpi_unaffected",
        check_hpc_benchmarks_openmpi_unaffected,
    )


# --- Direct staging execution checks ---


@pytest.mark.order(346)
def test_hpc_benchmarks_per_tool_staging_report(host):
    """TC-08: Rerun pull_benchmarks.sh and verify per-tool SUCCESS/SKIP report."""
    verify_pxeboot(
        host,
        "hpc_benchmarks_per_tool_staging_report",
        check_hpc_benchmarks_per_tool_staging_report,
    )


@pytest.mark.order(347)
def test_hpc_benchmarks_airgapped_staging(host):
    """TC-11: Verify staging succeeds while external egress is unavailable."""
    verify_pxeboot(
        host,
        "hpc_benchmarks_airgapped_staging",
        check_hpc_benchmarks_airgapped_staging,
    )


@pytest.mark.order(348)
def test_hpc_benchmarks_existing_dirs_preserved(host):
    """TC-18: Verify pre-existing /hpc_tools subdirs survive a staging run."""
    verify_pxeboot(
        host,
        "hpc_benchmarks_existing_dirs_preserved",
        check_hpc_benchmarks_existing_dirs_preserved,
    )


@pytest.mark.order(349)
def test_hpc_benchmarks_staging_idempotency(host):
    """TC-19: Verify a second staging run keeps the /hpc_tools snapshot stable."""
    verify_pxeboot(
        host,
        "hpc_benchmarks_staging_idempotency",
        check_hpc_benchmarks_staging_idempotency,
    )
