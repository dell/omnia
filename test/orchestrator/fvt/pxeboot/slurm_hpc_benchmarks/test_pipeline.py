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

"""HPC benchmarks end-to-end and adjacent-flow invariance checks."""

import pytest
from library.functions import (
    check_hpc_benchmarks_container_image_unaffected,
    check_hpc_benchmarks_cuda_flow_unaffected,
    check_hpc_benchmarks_e2e_provisioning,
    check_hpc_benchmarks_nvhpc_flow_unaffected,
    check_hpc_benchmarks_openmpi_unaffected,
)

from fvt.result import verify_pxeboot

pytestmark = [pytest.mark.slurm, pytest.mark.non_disruptive]


@pytest.mark.sanity
@pytest.mark.order(270)
def test_hpc_benchmarks_e2e_provisioning(host):
    """TC-09: Verify the end-to-end benchmark provisioning pipeline."""
    verify_pxeboot(
        host, "hpc_benchmarks_e2e_provisioning", check_hpc_benchmarks_e2e_provisioning
    )


@pytest.mark.functional
@pytest.mark.order(271)
def test_hpc_benchmarks_cuda_flow_unaffected(host):
    """TC-14: Verify /hpc_tools/cuda is unchanged after benchmark staging."""
    verify_pxeboot(
        host,
        "hpc_benchmarks_cuda_flow_unaffected",
        check_hpc_benchmarks_cuda_flow_unaffected,
    )


@pytest.mark.functional
@pytest.mark.order(272)
def test_hpc_benchmarks_nvhpc_flow_unaffected(host):
    """TC-15: Verify /hpc_tools/nvidia_sdk is unchanged after staging."""
    verify_pxeboot(
        host,
        "hpc_benchmarks_nvhpc_flow_unaffected",
        check_hpc_benchmarks_nvhpc_flow_unaffected,
    )


@pytest.mark.functional
@pytest.mark.order(273)
def test_hpc_benchmarks_container_image_unaffected(host):
    """TC-16: Verify /hpc_tools/container_images is unchanged after staging."""
    verify_pxeboot(
        host,
        "hpc_benchmarks_container_image_unaffected",
        check_hpc_benchmarks_container_image_unaffected,
    )


@pytest.mark.functional
@pytest.mark.order(274)
def test_hpc_benchmarks_openmpi_unaffected(host):
    """TC-17: Verify OpenMPI/UCX discovery is stable across a staging run."""
    verify_pxeboot(
        host,
        "hpc_benchmarks_openmpi_unaffected",
        check_hpc_benchmarks_openmpi_unaffected,
    )
