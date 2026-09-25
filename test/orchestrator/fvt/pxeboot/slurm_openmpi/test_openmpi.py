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

"""Slurm OpenMPI installation and workload contracts."""

import pytest
from library.functions import (
    check_slurm_openmpi_installation,
    check_slurm_openmpi_job,
)

from fvt.result import verify_pxeboot

pytestmark = [
    pytest.mark.sanity,
    pytest.mark.slurm,
    pytest.mark.non_disruptive,
]


@pytest.mark.order(257)
def test_slurm_openmpi_installation(host):
    """Verify OpenMPI discovery and version on every compute node."""
    verify_pxeboot(host, "slurm_openmpi_installation", check_slurm_openmpi_installation)


@pytest.mark.functional
@pytest.mark.order(258)
def test_slurm_openmpi_job(host):
    """Run an OpenMPI-backed job when OpenMPI is configured."""
    verify_pxeboot(host, "slurm_openmpi_job", check_slurm_openmpi_job)
