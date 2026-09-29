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

"""Slurm GPU inventory, allocation, and bounded-memory contracts."""

import pytest
from library.functions import (
    check_slurm_gpu_inventory,
    check_slurm_gpu_job,
    check_slurm_gpu_memory_stress,
)

from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.sanity,
    pytest.mark.slurm,
    pytest.mark.non_disruptive,
]


@pytest.mark.order(254)
def test_slurm_gpu_inventory(host):
    """Verify NVIDIA runtime state on scheduler-declared GPU nodes."""
    verify_pxeboot(host, "slurm_gpu_inventory", check_slurm_gpu_inventory)


@pytest.mark.functional
@pytest.mark.order(255)
def test_slurm_gpu_job(host):
    """Allocate a GPU through Slurm and query the device."""
    verify_pxeboot(host, "slurm_gpu_job", check_slurm_gpu_job)


@pytest.mark.functional
@pytest.mark.order(256)
def test_slurm_gpu_memory_stress(host):
    """Compile and run a bounded GPU memory workload through Slurm."""
    verify_pxeboot(host, "slurm_gpu_memory", check_slurm_gpu_memory_stress)
