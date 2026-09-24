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

"""Read-only HPC software, InfiniBand, and UCX fabric verification."""

import pytest
from library.functions import (
    check_slurm_gpu_inventory,
    check_slurm_infiniband_configuration,
    check_slurm_infiniband_connectivity,
    check_slurm_openmpi_installation,
    check_slurm_ucx_transport,
)

from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.sanity,
    pytest.mark.slurm,
    pytest.mark.non_disruptive,
]


@pytest.mark.order(247)
def test_slurm_openmpi_installation(host):
    """Verify OpenMPI discovery and version on every compute node."""
    verify_pxeboot(host, "slurm_openmpi_installation", check_slurm_openmpi_installation)


@pytest.mark.order(248)
def test_slurm_gpu_inventory(host):
    """Verify NVIDIA runtime state on scheduler-declared GPU nodes."""
    verify_pxeboot(host, "slurm_gpu_inventory", check_slurm_gpu_inventory)


@pytest.mark.order(253)
def test_slurm_infiniband_configuration(host):
    """Verify mapped IB interface, address, prefix, link, MTU, and OFED."""
    verify_pxeboot(host, "slurm_ib_configuration", check_slurm_infiniband_configuration)


@pytest.mark.order(254)
def test_slurm_infiniband_connectivity(host):
    """Verify every mapped IB endpoint can reach every mapped peer."""
    verify_pxeboot(host, "slurm_ib_connectivity", check_slurm_infiniband_connectivity)


@pytest.mark.order(255)
def test_slurm_ucx_transport(host):
    """Verify UCX exposes an InfiniBand-capable transport."""
    verify_pxeboot(host, "slurm_ucx_transport", check_slurm_ucx_transport)
