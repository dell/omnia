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

"""Opt-in GPU and InfiniBand visibility inside Apptainer containers."""

import pytest
from library.functions import (
    check_apptainer_cuda_workload,
    check_apptainer_gpu_access,
    check_apptainer_gpu_count,
    check_apptainer_gpu_memory,
    check_apptainer_infiniband,
)

from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.apptainer,
    pytest.mark.sanity,
    pytest.mark.functional,
    pytest.mark.non_disruptive,
]


@pytest.mark.order(287)
def test_apptainer_gpu_access(host):
    """Verify scheduler-declared GPU nodes expose GPUs in the container."""
    verify_pxeboot(host, "apptainer_gpu_access", check_apptainer_gpu_access)


@pytest.mark.order(288)
def test_apptainer_gpu_count(host):
    """Verify each container sees the same GPU count as its host."""
    verify_pxeboot(host, "apptainer_gpu_count", check_apptainer_gpu_count)


@pytest.mark.order(289)
def test_apptainer_cuda_workload(host):
    """Execute a bounded NVIDIA device query in each GPU container."""
    verify_pxeboot(host, "apptainer_cuda_workload", check_apptainer_cuda_workload)


@pytest.mark.order(290)
def test_apptainer_gpu_memory(host):
    """Verify the GPU query leaves no material device-memory allocation."""
    verify_pxeboot(host, "apptainer_gpu_memory", check_apptainer_gpu_memory)


@pytest.mark.order(291)
def test_apptainer_infiniband(host):
    """Verify mapped compute nodes expose InfiniBand devices in containers."""
    verify_pxeboot(host, "apptainer_infiniband", check_apptainer_infiniband)
